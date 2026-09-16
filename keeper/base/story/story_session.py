# -*- coding: utf-8 -*-
"""故事运行时会话：StorySession。"""
from __future__ import annotations

import random
from typing import Any, Callable, Optional

from keeper.base.investigator import Investigator
from keeper.base.story.model import (
    CheckCondition,
    CustomAction,
    EdgeKind,
    FlagCondition,
    StoryAction,
    StoryEdge,
    StoryNode,
    StoryNodeType,
    StoryOption,
    StorySnapshot,
)
from keeper.base.story.story_graph import StoryGraph

class StorySession:
    """单局游戏状态：游标、历史、flag、条件求值。"""

    def __init__(
        self,
        graph: StoryGraph,
        init: Optional[dict[str, Any]] = None,
    ) -> None:
        init = init or {}
        self.graph = graph
        self.current_node_id: str = init.get("start_node_id") or graph.start_node_id
        self.visited: list[str] = []
        self.visit_count: dict[str, int] = {}
        self.flags: dict[str, FlagValue] = dict(init.get("flags") or {})
        self._rng: Callable[[], float] = init.get("rng") or random.random
        self._check_resolver: Optional[Callable[[CheckCondition], bool]] = init.get(
            "check_resolver"
        )
        self._investigator: Optional[Investigator] = init.get("investigator")
        self._action_handler: Optional[Callable[[CustomAction], None]] = init.get(
            "action_handler"
        )
        self._record_visit()

    # ---------- 状态 ----------

    def start(self, clear_flags: bool = True) -> StoryNode:
        self.visited = []
        self.visit_count = {}
        if clear_flags:
            self.flags = {}
        self.current_node_id = self.graph.start_node_id
        self._record_visit()
        return self.get_current()

    def get_current(self) -> StoryNode:
        node = self.graph.get_node(self.current_node_id)
        if node is None:
            raise KeyError(f"current node not found: {self.current_node_id}")
        return node

    def is_finished(self) -> bool:
        return self.get_current().type == StoryNodeType.END

    # ---------- 查询可走边 ----------

    def get_available_edges(self) -> list[StoryEdge]:
        edges = [
            e
            for e in self.graph.get_outgoing_edges(self.current_node_id)
            if self.evaluate(e.condition)
        ]
        edges.sort(key=lambda e: e.priority, reverse=True)
        return edges

    def get_options(self) -> list[StoryOption]:
        options = []
        for e in self.get_available_edges():
            if e.kind == EdgeKind.CHOICE and e.label:
                options.append(StoryOption(edge_id=e.id, label=e.label, edge=e))
        return options

    # ---------- 流转 ----------

    def choose(self, edge_id: str) -> StoryNode:
        edge = self.graph.get_edge(edge_id)
        if edge is None:
            raise KeyError(f"edge not found: {edge_id}")
        if edge.from_node != self.current_node_id:
            raise ValueError(
                f"edge {edge_id} does not start from current node {self.current_node_id}"
            )
        current = self.get_current()
        target = self.graph.get_node(edge.to)
        if target is None:
            raise KeyError(f"target node not found: {edge.to}")

        self._apply_actions(current.exit_actions)
        self.current_node_id = target.id
        self._apply_actions(target.enter_actions)
        self._record_visit()
        return target

    def advance(self, max_steps: int = 100) -> Optional[StoryNode]:
        moved = False
        for _ in range(max_steps):
            if self.is_finished():
                break
            available = self.get_available_edges()
            auto_edges = [e for e in available if e.kind == EdgeKind.AUTO]
            if len(auto_edges) == 1:
                self.choose(auto_edges[0].id)
                moved = True
            else:
                break
        return self.get_current() if moved else None

    # ---------- 条件求值 ----------

    def evaluate(self, condition: Optional[Condition]) -> bool:
        if condition is None:
            return True
        kind = condition.kind
        if kind == "always":
            return True
        if kind == "flag":
            return self._eval_flag(condition)
        if kind == "check":
            return self._eval_check(condition)
        if kind == "random":
            return self._rng() < condition.chance
        if kind == "not":
            return not self.evaluate(condition.condition)
        if kind == "all":
            return all(self.evaluate(c) for c in condition.conditions)
        if kind == "any":
            return any(self.evaluate(c) for c in condition.conditions)
        return False

    def _eval_flag(self, condition: FlagCondition) -> bool:
        present = condition.flag in self.flags
        if condition.op == "exists":
            return present
        if condition.op == "not-exists":
            return not present
        if not present:
            return False
        actual = self.flags[condition.flag]
        expected = condition.value
        try:
            if condition.op == "==":
                return actual == expected
            if condition.op == "!=":
                return actual != expected
            if condition.op == ">":
                return actual > expected  # type: ignore[operator]
            if condition.op == "<":
                return actual < expected  # type: ignore[operator]
            if condition.op == ">=":
                return actual >= expected  # type: ignore[operator]
            if condition.op == "<=":
                return actual <= expected  # type: ignore[operator]
        except TypeError:
            return False
        return False

    def _eval_check(self, condition: CheckCondition) -> bool:
        if self._check_resolver is not None:
            return bool(self._check_resolver(condition))
        if self._investigator is not None:
            if condition.skill_id:
                result = self._investigator.check_skill(
                    condition.skill_id, condition.difficulty, self._rng
                )
            elif condition.attribute is not None:
                result = self._investigator.check_attribute(
                    condition.attribute, condition.difficulty, self._rng
                )
            else:
                return False
            if result is None:
                return False
            return result.success == condition.require_success
        return False

    # ---------- flag ----------

    def get_flag(self, flag: str) -> Optional[FlagValue]:
        return self.flags.get(flag)

    def set_flag(self, flag: str, value: FlagValue) -> None:
        self.flags[flag] = value

    # ---------- 动作 ----------

    def _apply_actions(self, actions: list[StoryAction]) -> None:
        for action in actions:
            if action.kind == "setFlag":
                self.flags[action.flag] = action.value
            elif action.kind == "incFlag":
                self.flags[action.flag] = (self.flags.get(action.flag, 0) or 0) + action.delta
            elif action.kind == "clearFlag":
                self.flags.pop(action.flag, None)
            elif action.kind == "custom":
                if self._action_handler is not None:
                    self._action_handler(action)

    # ---------- 内部 ----------

    def _record_visit(self) -> None:
        self.visited.append(self.current_node_id)
        self.visit_count[self.current_node_id] = (
            self.visit_count.get(self.current_node_id, 0) + 1
        )

    # ---------- 存档 / 读档 ----------

    def snapshot(self) -> StorySnapshot:
        return StorySnapshot(
            current_node_id=self.current_node_id,
            visited=list(self.visited),
            visit_count=dict(self.visit_count),
            flags=dict(self.flags),
        )

    def restore(self, snapshot: StorySnapshot) -> None:
        self.current_node_id = snapshot.current_node_id
        self.visited = list(snapshot.visited)
        self.visit_count = dict(snapshot.visit_count)
        self.flags = dict(snapshot.flags)
