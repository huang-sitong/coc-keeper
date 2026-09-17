# -*- coding: utf-8 -*-
"""故事图：PlotGraph。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import PrivateAttr

from keeper.base.module.model import (
    EdgeKind,
    PlotEdge,
    PlotGraphData,
    PlotNode,
    PlotNodeType,
    PlotValidation,
)

class PlotGraph(PlotGraphData):
    """故事流程图：只描述结构，不保存运行状态。"""

    _node_index: Optional[dict[str, PlotNode]] = PrivateAttr(default=None)
    _edge_index: Optional[dict[str, PlotEdge]] = PrivateAttr(default=None)
    _from_index: Optional[dict[str, list[PlotEdge]]] = PrivateAttr(default=None)
    _to_index: Optional[dict[str, list[PlotEdge]]] = PrivateAttr(default=None)

    # ---------- 索引 ----------

    def _ensure_indexes(self) -> None:
        if self._node_index is None:
            self._node_index = {n.id: n for n in self.nodes}
        if self._edge_index is None:
            self._edge_index = {e.id: e for e in self.edges}
        if self._from_index is None:
            self._from_index = {}
            for e in self.edges:
                self._from_index.setdefault(e.from_node, []).append(e)
        if self._to_index is None:
            self._to_index = {}
            for e in self.edges:
                self._to_index.setdefault(e.to, []).append(e)

    def _invalidate_indexes(self) -> None:
        self._node_index = None
        self._edge_index = None
        self._from_index = None
        self._to_index = None

    # ---------- 查询 ----------

    def get_node(self, node_id: str) -> Optional[PlotNode]:
        self._ensure_indexes()
        return self._node_index.get(node_id)  # type: ignore[union-attr]

    def get_edge(self, edge_id: str) -> Optional[PlotEdge]:
        self._ensure_indexes()
        return self._edge_index.get(edge_id)  # type: ignore[union-attr]

    def get_start_node(self) -> PlotNode:
        node = self.get_node(self.start_node_id)
        if node is None:
            raise KeyError(f"start node not found: {self.start_node_id}")
        return node

    def get_outgoing_edges(self, node_id: str) -> list[PlotEdge]:
        self._ensure_indexes()
        return list(self._from_index.get(node_id, []))  # type: ignore[union-attr]

    def get_incoming_edges(self, node_id: str) -> list[PlotEdge]:
        self._ensure_indexes()
        return list(self._to_index.get(node_id, []))  # type: ignore[union-attr]

    def get_choice_options(self, node_id: str) -> list[PlotEdge]:
        return [
            e
            for e in self.get_outgoing_edges(node_id)
            if e.kind == EdgeKind.CHOICE and e.label
        ]

    # ---------- 增删改 ----------

    def add_node(self, node: PlotNode) -> bool:
        if self.get_node(node.id) is not None:
            return False
        self.nodes.append(node)
        self._invalidate_indexes()
        return True

    def update_node(self, node_id: str, patch: dict[str, Any]) -> bool:
        node = self.get_node(node_id)
        if node is None:
            return False
        for key, value in patch.items():
            if key != "id":
                setattr(node, key, value)
        self._invalidate_indexes()
        return True

    def remove_node(self, node_id: str) -> bool:
        node = self.get_node(node_id)
        if node is None:
            return False
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [
            e for e in self.edges if e.from_node != node_id and e.to != node_id
        ]
        self._invalidate_indexes()
        return True

    def add_edge(self, edge: PlotEdge) -> bool:
        if self.get_edge(edge.id) is not None:
            return False
        if self.get_node(edge.from_node) is None or self.get_node(edge.to) is None:
            return False
        self.edges.append(edge)
        self._invalidate_indexes()
        return True

    def update_edge(self, edge_id: str, patch: dict[str, Any]) -> bool:
        edge = self.get_edge(edge_id)
        if edge is None:
            return False
        for key, value in patch.items():
            if key != "id":
                setattr(edge, key, value)
        self._invalidate_indexes()
        return True

    def remove_edge(self, edge_id: str) -> bool:
        edge = self.get_edge(edge_id)
        if edge is None:
            return False
        self.edges = [e for e in self.edges if e.id != edge_id]
        self._invalidate_indexes()
        return True

    # ---------- 校验 / 序列化 ----------

    def validate(self) -> PlotValidation:
        errors: list[str] = []
        warnings: list[str] = []

        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            errors.append("存在重复节点 id")
        if self.get_node(self.start_node_id) is None:
            errors.append(f"起始节点不存在: {self.start_node_id}")

        edge_ids = [e.id for e in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            errors.append("存在重复边 id")

        for e in self.edges:
            if self.get_node(e.from_node) is None:
                errors.append(f"边 {e.id} 的 from 节点不存在: {e.from_node}")
            if self.get_node(e.to) is None:
                errors.append(f"边 {e.id} 的 to 节点不存在: {e.to}")

        start_count = sum(1 for n in self.nodes if n.type == PlotNodeType.START)
        if start_count == 0:
            errors.append("缺少 START 节点")
        elif start_count > 1:
            warnings.append(f"存在多个 START 节点: {start_count}")

        for n in self.nodes:
            if n.type != PlotNodeType.END and not self.get_outgoing_edges(n.id):
                warnings.append(f"非 END 节点没有出边: {n.id}")

        return PlotValidation(ok=not errors, errors=errors, warnings=warnings)
