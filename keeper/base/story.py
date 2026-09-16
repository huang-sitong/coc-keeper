# -*- coding: utf-8 -*-
"""COC 故事流程图 / 模组素材模型。

依据 :doc:`/StoryGraghDesignSpec` 设计，使用 Pydantic 建模。
包含：
- 故事图：StoryGraph / StorySession
- 模组素材：StoryModuleData / StoryModule
- Agent 上下文组装：StoryAgentContext
"""
from __future__ import annotations

import random
from enum import Enum
from typing import Annotated, Any, Callable, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from keeper.base.investigator import (
    AttributeName,
    Attributes,
    Difficulty,
    Investigator,
    SkillGroups,
    WeaponList,
)

__all__ = [
    "StoryNodeType",
    "EdgeKind",
    "Visibility",
    "FlagValue",
    "StoryAction",
    "SetFlagAction",
    "IncFlagAction",
    "ClearFlagAction",
    "CustomAction",
    "Condition",
    "AlwaysCondition",
    "FlagCondition",
    "CheckCondition",
    "RandomCondition",
    "NotCondition",
    "AllCondition",
    "AnyCondition",
    "StoryNode",
    "StoryEdge",
    "StoryGraphData",
    "StoryValidation",
    "StoryGraph",
    "StorySnapshot",
    "StoryOption",
    "StorySession",
    "StoryMeta",
    "NpcCard",
    "Creature",
    "ItemCard",
    "ClueCard",
    "HandoutCard",
    "Secret",
    "StoryModuleData",
    "StoryModule",
    "AgentContextOptions",
    "StoryAgentContext",
]


class StoryBaseModel(BaseModel):
    """统一允许 snake_case 字段名 + camelCase JSON alias。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


# ==================== 基础类型 ====================


class StoryNodeType(str, Enum):
    """节点类型。"""

    START = "start"
    SCENE = "scene"
    END = "end"


class EdgeKind(str, Enum):
    """边类型。"""

    AUTO = "auto"
    CHOICE = "choice"
    CONDITION = "condition"


class Visibility(str, Enum):
    """可见性：玩家可见 / 仅守密人可见。"""

    PUBLIC = "public"
    KEEPER = "keeper"


FlagValue = Union[bool, int, str]


# ==================== 动作 ====================


class SetFlagAction(StoryBaseModel):
    kind: Literal["setFlag"]
    flag: str
    value: FlagValue


class IncFlagAction(StoryBaseModel):
    kind: Literal["incFlag"]
    flag: str
    delta: int


class ClearFlagAction(StoryBaseModel):
    kind: Literal["clearFlag"]
    flag: str


class CustomAction(StoryBaseModel):
    kind: Literal["custom"]
    type: str
    payload: Any = None


StoryAction = Annotated[
    Union[SetFlagAction, IncFlagAction, ClearFlagAction, CustomAction],
    Field(discriminator="kind"),
]


# ==================== 条件 ====================


class AlwaysCondition(StoryBaseModel):
    kind: Literal["always"]


class FlagCondition(StoryBaseModel):
    kind: Literal["flag"]
    flag: str
    op: Literal["exists", "not-exists", "==", "!=", ">", "<", ">=", "<="]
    value: Optional[FlagValue] = None


class CheckCondition(StoryBaseModel):
    kind: Literal["check"]
    skill_id: Optional[str] = Field(default=None, alias="skillId")
    attribute: Optional[AttributeName] = None
    difficulty: Difficulty = Difficulty.NORMAL
    require_success: bool = Field(default=True, alias="requireSuccess")


class RandomCondition(StoryBaseModel):
    kind: Literal["random"]
    chance: float


class NotCondition(StoryBaseModel):
    kind: Literal["not"]
    condition: Condition


class AllCondition(StoryBaseModel):
    kind: Literal["all"]
    conditions: list[Condition]


class AnyCondition(StoryBaseModel):
    kind: Literal["any"]
    conditions: list[Condition]


Condition = Annotated[
    Union[
        AlwaysCondition,
        FlagCondition,
        CheckCondition,
        RandomCondition,
        NotCondition,
        AllCondition,
        AnyCondition,
    ],
    Field(discriminator="kind"),
]


# ==================== 节点与边 ====================


class StoryNode(StoryBaseModel):
    """故事节点：场景/剧情段。"""

    id: str
    type: StoryNodeType
    title: str
    text: str
    enter_actions: list[StoryAction] = Field(default_factory=list, alias="enterActions")
    exit_actions: list[StoryAction] = Field(default_factory=list, alias="exitActions")
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryEdge(StoryBaseModel):
    """故事边：节点间转移。"""

    id: str
    from_node: str = Field(alias="from")
    to: str
    kind: EdgeKind
    label: Optional[str] = None
    condition: Optional[Condition] = None
    priority: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryGraphData(StoryBaseModel):
    """故事图 JSON 数据形态。"""

    id: str
    title: str
    description: str = ""
    start_node_id: str = Field(alias="startNodeId")
    nodes: list[StoryNode] = Field(default_factory=list)
    edges: list[StoryEdge] = Field(default_factory=list)


class StoryValidation(StoryBaseModel):
    """校验结果。"""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ==================== 故事图 ====================


class StoryGraph(StoryGraphData):
    """故事流程图：只描述结构，不保存运行状态。"""

    _node_index: Optional[dict[str, StoryNode]] = PrivateAttr(default=None)
    _edge_index: Optional[dict[str, StoryEdge]] = PrivateAttr(default=None)
    _from_index: Optional[dict[str, list[StoryEdge]]] = PrivateAttr(default=None)
    _to_index: Optional[dict[str, list[StoryEdge]]] = PrivateAttr(default=None)

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

    def get_node(self, node_id: str) -> Optional[StoryNode]:
        self._ensure_indexes()
        return self._node_index.get(node_id)  # type: ignore[union-attr]

    def get_edge(self, edge_id: str) -> Optional[StoryEdge]:
        self._ensure_indexes()
        return self._edge_index.get(edge_id)  # type: ignore[union-attr]

    def get_start_node(self) -> StoryNode:
        node = self.get_node(self.start_node_id)
        if node is None:
            raise KeyError(f"start node not found: {self.start_node_id}")
        return node

    def get_outgoing_edges(self, node_id: str) -> list[StoryEdge]:
        self._ensure_indexes()
        return list(self._from_index.get(node_id, []))  # type: ignore[union-attr]

    def get_incoming_edges(self, node_id: str) -> list[StoryEdge]:
        self._ensure_indexes()
        return list(self._to_index.get(node_id, []))  # type: ignore[union-attr]

    def get_choice_options(self, node_id: str) -> list[StoryEdge]:
        return [
            e
            for e in self.get_outgoing_edges(node_id)
            if e.kind == EdgeKind.CHOICE and e.label
        ]

    # ---------- 增删改 ----------

    def add_node(self, node: StoryNode) -> bool:
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

    def add_edge(self, edge: StoryEdge) -> bool:
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

    def validate(self) -> StoryValidation:
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

        start_count = sum(1 for n in self.nodes if n.type == StoryNodeType.START)
        if start_count == 0:
            errors.append("缺少 START 节点")
        elif start_count > 1:
            warnings.append(f"存在多个 START 节点: {start_count}")

        for n in self.nodes:
            if n.type != StoryNodeType.END and not self.get_outgoing_edges(n.id):
                warnings.append(f"非 END 节点没有出边: {n.id}")

        return StoryValidation(ok=not errors, errors=errors, warnings=warnings)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StoryGraph":
        return cls.model_validate(data)


# ==================== 运行时会话 ====================


class StorySnapshot(StoryBaseModel):
    """会话存档。"""

    current_node_id: str = Field(alias="currentNodeId")
    visited: list[str] = Field(default_factory=list)
    visit_count: dict[str, int] = Field(default_factory=dict, alias="visitCount")
    flags: dict[str, FlagValue] = Field(default_factory=dict)


class StoryOption(StoryBaseModel):
    """玩家可见选项。"""

    edge_id: str = Field(alias="edgeId")
    label: str
    edge: StoryEdge


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


# ==================== 模组素材 ====================


class StoryMeta(StoryBaseModel):
    """模组元信息。"""

    id: str
    title: str
    era: str = ""
    location: str = ""
    summary: str = ""
    background: str = ""
    hook: str = ""
    tone: Optional[str] = None
    expected_length: Optional[str] = Field(default=None, alias="expectedLength")
    ending_conditions: list[str] = Field(default_factory=list, alias="endingConditions")


class NpcCard(StoryBaseModel):
    """NPC 卡片。"""

    id: str
    name: str
    role: str = ""
    appearance: Optional[str] = None
    personality: Optional[str] = None
    public_notes: Optional[str] = Field(default=None, alias="publicNotes")
    keeper_notes: Optional[str] = Field(default=None, alias="keeperNotes")
    secrets: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    appears_in: list[str] = Field(default_factory=list, alias="appearsIn")


class Creature(StoryBaseModel):
    """敌人/怪物：叙述字段与详细战斗数据合并为单个数据类。

    属性复用 ``Attributes``，技能复用 ``SkillGroups``，武器复用 ``WeaponList``；
    HP/MP/SAN/DB/Build/Move/Armor 直接以模组给出的数值记录。
    """

    id: str
    name: str
    appearance: Optional[str] = None
    appears_in: list[str] = Field(default_factory=list, alias="appearsIn")

    # 详细战斗数据（类似简化版调查员）
    attributes: Attributes = Field(default_factory=Attributes)
    hp: int = 0
    mp: int = 0
    sanity: int = 0
    db: str = "0"
    build: int = 0
    move: int = 8
    armor: str = "0"
    skills: SkillGroups = Field(default_factory=SkillGroups)
    weapons: WeaponList = Field(default_factory=WeaponList)
    spells: list[str] = Field(default_factory=list)
    attacks: list[str] = Field(default_factory=list)
    sanity_loss: Optional[str] = Field(default=None, alias="sanityLoss")
    tactics: Optional[str] = None


class ItemCard(StoryBaseModel):
    """物品卡片。"""

    id: str
    name: str
    public_description: Optional[str] = Field(default=None, alias="publicDescription")
    keeper_effects: Optional[str] = Field(default=None, alias="keeperEffects")
    hidden_properties: list[str] = Field(default_factory=list, alias="hiddenProperties")
    location: Optional[str] = None
    obtained_by: list[str] = Field(default_factory=list, alias="obtainedBy")
    appears_in: list[str] = Field(default_factory=list, alias="appearsIn")


class ClueCard(StoryBaseModel):
    """线索卡片。"""

    id: str
    title: str
    content: str
    visibility: Visibility = Visibility.PUBLIC
    reveal_condition: Optional[Condition] = Field(default=None, alias="revealCondition")
    source_node: Optional[str] = Field(default=None, alias="sourceNode")
    related_npc_ids: list[str] = Field(default_factory=list, alias="relatedNpcIds")
    related_item_ids: list[str] = Field(default_factory=list, alias="relatedItemIds")
    related_clue_ids: list[str] = Field(default_factory=list, alias="relatedClueIds")


class HandoutCard(StoryBaseModel):
    """给玩家的文字材料。"""

    id: str
    title: str
    content: str
    image_ref: Optional[str] = Field(default=None, alias="imageRef")
    given_by: Optional[str] = Field(default=None, alias="givenBy")
    reveal_condition: Optional[Condition] = Field(default=None, alias="revealCondition")


class Secret(StoryBaseModel):
    """仅守密人知道的秘密。"""

    id: str
    title: str
    content: str
    reveal_condition: Optional[Condition] = Field(default=None, alias="revealCondition")
    related_npc_ids: list[str] = Field(default_factory=list, alias="relatedNpcIds")
    related_clue_ids: list[str] = Field(default_factory=list, alias="relatedClueIds")


class StoryModuleData(StoryBaseModel):
    """模组总包：流程 + 素材。"""

    meta: StoryMeta
    graph: StoryGraph
    npcs: list[NpcCard] = Field(default_factory=list)
    creatures: list[Creature] = Field(default_factory=list)
    items: list[ItemCard] = Field(default_factory=list)
    clues: list[ClueCard] = Field(default_factory=list)
    handouts: list[HandoutCard] = Field(default_factory=list)
    secrets: list[Secret] = Field(default_factory=list)


class StoryModule(StoryModuleData):
    """模组包：加载全部素材，提供索引与按需检索。"""

    _npc_index: Optional[dict[str, NpcCard]] = PrivateAttr(default=None)
    _creature_index: Optional[dict[str, Creature]] = PrivateAttr(default=None)
    _item_index: Optional[dict[str, ItemCard]] = PrivateAttr(default=None)
    _clue_index: Optional[dict[str, ClueCard]] = PrivateAttr(default=None)
    _handout_index: Optional[dict[str, HandoutCard]] = PrivateAttr(default=None)
    _secret_index: Optional[dict[str, Secret]] = PrivateAttr(default=None)

    def _ensure_indexes(self) -> None:
        if self._npc_index is None:
            self._npc_index = {x.id: x for x in self.npcs}
        if self._creature_index is None:
            self._creature_index = {x.id: x for x in self.creatures}
        if self._item_index is None:
            self._item_index = {x.id: x for x in self.items}
        if self._clue_index is None:
            self._clue_index = {x.id: x for x in self.clues}
        if self._handout_index is None:
            self._handout_index = {x.id: x for x in self.handouts}
        if self._secret_index is None:
            self._secret_index = {x.id: x for x in self.secrets}

    def get_npc(self, npc_id: str) -> Optional[NpcCard]:
        self._ensure_indexes()
        return self._npc_index.get(npc_id)  # type: ignore[union-attr]

    def get_creature(self, creature_id: str) -> Optional[Creature]:
        self._ensure_indexes()
        return self._creature_index.get(creature_id)  # type: ignore[union-attr]

    def get_item(self, item_id: str) -> Optional[ItemCard]:
        self._ensure_indexes()
        return self._item_index.get(item_id)  # type: ignore[union-attr]

    def get_clue(self, clue_id: str) -> Optional[ClueCard]:
        self._ensure_indexes()
        return self._clue_index.get(clue_id)  # type: ignore[union-attr]

    def get_handout(self, handout_id: str) -> Optional[HandoutCard]:
        self._ensure_indexes()
        return self._handout_index.get(handout_id)  # type: ignore[union-attr]

    def get_secret(self, secret_id: str) -> Optional[Secret]:
        self._ensure_indexes()
        return self._secret_index.get(secret_id)  # type: ignore[union-attr]

    def get_entities_for_node(
        self, node_id: str
    ) -> dict[str, list[Any]]:
        npcs = [x for x in self.npcs if node_id in x.appears_in]
        creatures = [x for x in self.creatures if node_id in x.appears_in]
        items = [x for x in self.items if node_id in x.appears_in]
        clues = [x for x in self.clues if node_id == x.source_node]
        related_npc_ids = {x.id for x in npcs}
        related_clue_ids = {x.id for x in clues}
        secrets = [
            x
            for x in self.secrets
            if any(nid in related_npc_ids for nid in x.related_npc_ids)
            or any(cid in related_clue_ids for cid in x.related_clue_ids)
        ]
        return {
            "npcs": npcs,
            "creatures": creatures,
            "items": items,
            "clues": clues,
            "secrets": secrets,
        }

    def validate(self) -> StoryValidation:
        errors: list[str] = []
        warnings: list[str] = []

        graph_result = self.graph.validate()
        errors.extend(graph_result.errors)
        warnings.extend(graph_result.warnings)

        node_ids = {n.id for n in self.graph.nodes}
        collections = {
            "npcs": self.npcs,
            "creatures": self.creatures,
            "items": self.items,
            "clues": self.clues,
            "handouts": self.handouts,
            "secrets": self.secrets,
        }
        for name, items in collections.items():
            ids = [x.id for x in items]
            if len(ids) != len(set(ids)):
                errors.append(f"{name} 存在重复 id")

        for npc in self.npcs:
            for node_id in npc.appears_in:
                if node_id not in node_ids:
                    errors.append(f"NPC {npc.id} 引用了不存在的节点 {node_id}")
        for creature in self.creatures:
            for node_id in creature.appears_in:
                if node_id not in node_ids:
                    errors.append(f"敌人 {creature.id} 引用了不存在的节点 {node_id}")
        for item in self.items:
            for node_id in item.appears_in:
                if node_id not in node_ids:
                    errors.append(f"物品 {item.id} 引用了不存在的节点 {node_id}")
        for clue in self.clues:
            if clue.source_node and clue.source_node not in node_ids:
                errors.append(f"线索 {clue.id} 引用了不存在的来源节点 {clue.source_node}")
        for handout in self.handouts:
            if handout.given_by and handout.given_by not in node_ids:
                errors.append(f"Handout {handout.id} 引用了不存在的节点 {handout.given_by}")

        return StoryValidation(ok=not errors, errors=errors, warnings=warnings)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StoryModule":
        return cls.model_validate(data)


# ==================== Agent 上下文组装 ====================


class AgentContextOptions(StoryBaseModel):
    """Agent 上下文组装选项。"""

    include_keeper_info: bool = Field(default=True, alias="includeKeeperInfo")
    max_entities_per_scene: int = Field(default=10, alias="maxEntitiesPerScene")


class StoryAgentContext:
    """把模组素材 + 运行状态组装成给 LLM 的上下文。"""

    def __init__(
        self,
        module: StoryModule,
        session: StorySession,
        options: Optional[AgentContextOptions | dict[str, Any]] = None,
    ) -> None:
        self.module = module
        self.session = session
        if options is None:
            self.options = AgentContextOptions()
        elif isinstance(options, dict):
            self.options = AgentContextOptions(**options)
        else:
            self.options = options

    # ---------- Prompt 构建 ----------

    def build_system_prompt(self) -> str:
        meta = self.module.meta
        lines = [
            "你是一位《克苏鲁的呼唤》守密人（Keeper）。",
            "请根据模组信息、当前场景和调查员状态进行叙述与判定。",
            "",
            f"## 模组：{meta.title}",
            f"- 时代：{meta.era}",
            f"- 地点：{meta.location}",
            f"- 简介：{meta.summary}",
            f"- 背景：{meta.background}",
            f"- 开场钩子：{meta.hook}",
        ]
        if meta.tone:
            lines.append(f"- 氛围：{meta.tone}")
        if meta.expected_length:
            lines.append(f"- 预计时长：{meta.expected_length}")
        if meta.ending_conditions:
            lines.append(f"- 结局条件：{'；'.join(meta.ending_conditions)}")

        if self.options.include_keeper_info:
            lines.append("")
            lines.append("## 守密人专属信息（禁止主动向玩家泄露）")
            for secret in self.module.secrets:
                lines.append(f"- {secret.title}：{secret.content}")
            for npc in self.module.npcs:
                if npc.keeper_notes:
                    lines.append(f"- {npc.name}（守密人笔记）：{npc.keeper_notes}")
            for creature in self.module.creatures:
                if creature.tactics:
                    lines.append(f"- {creature.name}（战术）：{creature.tactics}")

        return "\n".join(lines)

    def build_scene_prompt(self) -> str:
        current = self.session.get_current()
        lines = [
            f"## 当前场景：{current.title}",
            current.text,
        ]
        options = self.session.get_options()
        if options:
            lines.append("")
            lines.append("### 玩家可选行动")
            for opt in options:
                lines.append(f"- {opt.label}")

        entities = self.module.get_entities_for_node(current.id)
        revealed_clue_ids = {c.id for c in self.get_revealed_clues()}
        for kind, cards in entities.items():
            if not cards:
                continue
            lines.append("")
            lines.append(f"### 相关{kind}")
            for card in cards[: self.options.max_entities_per_scene]:
                if kind == "npcs":
                    lines.append(f"- {card.name}（{card.role}）：{card.public_notes or card.appearance or ''}")
                elif kind == "creatures":
                    lines.append(f"- {card.name}：{card.appearance or ''}")
                elif kind == "items":
                    lines.append(f"- {card.name}：{card.public_description or ''}")
                elif kind == "clues":
                    if card.id in revealed_clue_ids:
                        lines.append(f"- {card.title}：{card.content}")
                elif kind == "secrets":
                    if self.options.include_keeper_info:
                        lines.append(f"- {card.title}：{card.content}")

        return "\n".join(lines)

    def build_state_prompt(self) -> str:
        lines = [
            "## 调查员当前状态",
            f"- 当前节点：{self.session.current_node_id}",
            f"- 访问历史：{' -> '.join(self.session.visited) or '无'}",
            f"- Flags：{self.session.flags or {}}",
        ]
        clues = self.get_revealed_clues()
        if clues:
            lines.append("")
            lines.append("### 调查员已获得线索")
            for clue in clues:
                lines.append(f"- {clue.title}：{clue.content}")
        return "\n".join(lines)

    def build_prompt(self) -> str:
        return "\n\n".join(
            [
                self.build_system_prompt(),
                self.build_scene_prompt(),
                self.build_state_prompt(),
            ]
        )

    # ---------- 按需检索 ----------

    def resolve_entity(
        self, kind: Literal["npc", "creature", "item", "clue", "handout"], entity_id: str
    ) -> str:
        if kind == "npc":
            card = self.module.get_npc(entity_id)
        elif kind == "creature":
            card = self.module.get_creature(entity_id)
        elif kind == "item":
            card = self.module.get_item(entity_id)
        elif kind == "clue":
            card = self.module.get_clue(entity_id)
        elif kind == "handout":
            card = self.module.get_handout(entity_id)
        else:
            return f"未知类型: {kind}"

        if card is None:
            return f"未找到 {kind}: {entity_id}"

        if kind in ("clue", "handout") and getattr(card, "reveal_condition", None) is not None:
            if not self.session.evaluate(card.reveal_condition):
                return f"{card.title} 尚未被调查员发现，暂时不能提供详细内容。"

        return self._format_card(kind, card)

    def _format_card(self, kind: str, card: Any) -> str:
        if kind == "npc":
            return (
                f"【NPC】{card.name}（{card.role}）\n"
                f"外貌：{card.appearance or ''}\n"
                f"性格：{card.personality or ''}\n"
                f"玩家可见：{card.public_notes or ''}\n"
                + (f"守密人笔记：{card.keeper_notes or ''}" if self.options.include_keeper_info else "")
            )
        if kind == "creature":
            attrs = card.attributes.model_dump(by_alias=True)
            skill_lines = []
            for group in card.skills.all_group_lists():
                for skill in group:
                    skill_lines.append(f"{skill.name} {skill.total}%")
            weapon_lines = [f"{w.name} {w.damage}" for w in card.weapons.items]
            lines = [
                f"【敌人】{card.name}",
                f"外貌：{card.appearance or ''}",
                f"属性：{attrs}",
                f"HP：{card.hp} MP：{card.mp} SAN：{card.sanity}",
                f"DB：{card.db} Build：{card.build} Move：{card.move}",
                f"护甲：{card.armor or ''}",
                f"技能：{'；'.join(skill_lines) or '无'}",
                f"武器：{'；'.join(weapon_lines) or '无'}",
                f"攻击：{'；'.join(card.attacks) or '无'}",
                f"法术：{'；'.join(card.spells) or '无'}",
            ]
            if self.options.include_keeper_info:
                if card.tactics:
                    lines.append(f"战术：{card.tactics}")
                if card.sanity_loss:
                    lines.append(f"理智损失：{card.sanity_loss}")
            return "\n".join(lines)
        if kind == "item":
            return (
                f"【物品】{card.name}\n"
                f"描述：{card.public_description or ''}\n"
                + (f"隐藏效果：{card.keeper_effects or ''}" if self.options.include_keeper_info else "")
            )
        if kind == "clue":
            return f"【线索】{card.title}\n{card.content}"
        if kind == "handout":
            return f"【文字材料】{card.title}\n{card.content}"
        return str(card)

    def get_revealed_clues(self) -> list[ClueCard]:
        revealed = []
        for clue in self.module.clues:
            if clue.visibility != Visibility.PUBLIC:
                continue
            if clue.reveal_condition is None or self.session.evaluate(clue.reveal_condition):
                revealed.append(clue)
        return revealed

    # ---------- Function Calling ----------

    def build_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_npc",
                "description": "获取 NPC 详细卡片",
                "parameters": {"type": "object", "properties": {"id": {"type": "string"}}},
            },
            {
                "name": "get_item",
                "description": "获取物品详细卡片",
                "parameters": {"type": "object", "properties": {"id": {"type": "string"}}},
            },
            {
                "name": "get_clue",
                "description": "获取线索详细卡片",
                "parameters": {"type": "object", "properties": {"id": {"type": "string"}}},
            },
            {
                "name": "get_creature",
                "description": "获取敌人/怪物详细卡片",
                "parameters": {"type": "object", "properties": {"id": {"type": "string"}}},
            },
            {
                "name": "choose",
                "description": "沿指定边推进剧情",
                "parameters": {"type": "object", "properties": {"edge_id": {"type": "string"}}},
            },
            {
                "name": "set_flag",
                "description": "设置剧情 flag",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "flag": {"type": "string"},
                        "value": {},
                    },
                },
            },
        ]
