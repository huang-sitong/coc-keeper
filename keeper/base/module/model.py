# -*- coding: utf-8 -*-
"""COC 故事流程图 / 模组素材：纯数据模型。

无自定义方法的基础数据类集中在此；敌人/怪物模型见
``keeper.base.creature``。
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import Field

from keeper.base.creature import Creature as _Creature
from keeper.base.investigator import AttributeName, Difficulty
from keeper.base.module_base import ModuleBaseModel


# ==================== 基础类型 ====================


class PlotNodeType(str, Enum):
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


class SetFlagAction(ModuleBaseModel):
    kind: Literal["setFlag"]
    flag: str
    value: FlagValue


class IncFlagAction(ModuleBaseModel):
    kind: Literal["incFlag"]
    flag: str
    delta: int


class ClearFlagAction(ModuleBaseModel):
    kind: Literal["clearFlag"]
    flag: str


class CustomAction(ModuleBaseModel):
    kind: Literal["custom"]
    type: str
    payload: Any = None


PlotAction = Annotated[
    Union[SetFlagAction, IncFlagAction, ClearFlagAction, CustomAction],
    Field(discriminator="kind"),
]


# ==================== 条件 ====================


class AlwaysCondition(ModuleBaseModel):
    kind: Literal["always"]


class FlagCondition(ModuleBaseModel):
    kind: Literal["flag"]
    flag: str
    op: Literal["exists", "not-exists", "==", "!=", ">", "<", ">=", "<="]
    value: Optional[FlagValue] = None


class CheckCondition(ModuleBaseModel):
    kind: Literal["check"]
    skill_id: Optional[str] = Field(default=None, alias="skillId")
    attribute: Optional[AttributeName] = None
    difficulty: Difficulty = Difficulty.NORMAL
    require_success: bool = Field(default=True, alias="requireSuccess")


class RandomCondition(ModuleBaseModel):
    kind: Literal["random"]
    chance: float


class NotCondition(ModuleBaseModel):
    kind: Literal["not"]
    condition: Condition


class AllCondition(ModuleBaseModel):
    kind: Literal["all"]
    conditions: list[Condition]


class AnyCondition(ModuleBaseModel):
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


class PlotNode(ModuleBaseModel):
    """故事节点：场景/剧情段。"""

    id: str
    type: PlotNodeType
    title: str
    text: str
    enter_actions: list[PlotAction] = Field(default_factory=list, alias="enterActions")
    exit_actions: list[PlotAction] = Field(default_factory=list, alias="exitActions")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlotEdge(ModuleBaseModel):
    """故事边：节点间转移。"""

    id: str
    from_node: str = Field(alias="from")
    to: str
    kind: EdgeKind
    label: Optional[str] = None
    condition: Optional[Condition] = None
    priority: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlotGraphData(ModuleBaseModel):
    """故事图 JSON 数据形态。"""

    id: str
    title: str
    description: str = ""
    start_node_id: str = Field(alias="startNodeId")
    nodes: list[PlotNode] = Field(default_factory=list)
    edges: list[PlotEdge] = Field(default_factory=list)


class PlotValidation(ModuleBaseModel):
    """校验结果。"""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)



# ==================== 运行时会话 ====================


class PlotSnapshot(ModuleBaseModel):
    """会话存档。"""

    current_node_id: str = Field(alias="currentNodeId")
    visited: list[str] = Field(default_factory=list)
    visit_count: dict[str, int] = Field(default_factory=dict, alias="visitCount")
    flags: dict[str, FlagValue] = Field(default_factory=dict)


class PlotOption(ModuleBaseModel):
    """玩家可见选项。"""

    edge_id: str = Field(alias="edgeId")
    label: str
    edge: PlotEdge



# ==================== 模组素材 ====================


class CocMeta(ModuleBaseModel):
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


class NpcCard(ModuleBaseModel):
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


class ItemCard(ModuleBaseModel):
    """物品卡片。"""

    id: str
    name: str
    public_description: Optional[str] = Field(default=None, alias="publicDescription")
    keeper_effects: Optional[str] = Field(default=None, alias="keeperEffects")
    hidden_properties: list[str] = Field(default_factory=list, alias="hiddenProperties")
    location: Optional[str] = None
    obtained_by: list[str] = Field(default_factory=list, alias="obtainedBy")
    appears_in: list[str] = Field(default_factory=list, alias="appearsIn")


class ClueCard(ModuleBaseModel):
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


class HandoutCard(ModuleBaseModel):
    """给玩家的文字材料。"""

    id: str
    title: str
    content: str
    image_ref: Optional[str] = Field(default=None, alias="imageRef")
    given_by: Optional[str] = Field(default=None, alias="givenBy")
    reveal_condition: Optional[Condition] = Field(default=None, alias="revealCondition")


class Secret(ModuleBaseModel):
    """仅守密人知道的秘密。"""

    id: str
    title: str
    content: str
    reveal_condition: Optional[Condition] = Field(default=None, alias="revealCondition")
    related_npc_ids: list[str] = Field(default_factory=list, alias="relatedNpcIds")
    related_clue_ids: list[str] = Field(default_factory=list, alias="relatedClueIds")


class CocModuleData(ModuleBaseModel):
    """模组总包：流程 + 素材。"""

    meta: CocMeta
    graph: PlotGraphData
    npcs: list[NpcCard] = Field(default_factory=list)
    creatures: list[_Creature] = Field(default_factory=list)
    items: list[ItemCard] = Field(default_factory=list)
    clues: list[ClueCard] = Field(default_factory=list)
    handouts: list[HandoutCard] = Field(default_factory=list)
    secrets: list[Secret] = Field(default_factory=list)



# ==================== Agent 上下文组装 ====================


class AgentContextOptions(ModuleBaseModel):
    """Agent 上下文组装选项。"""

    include_keeper_info: bool = Field(default=True, alias="includeKeeperInfo")
    max_entities_per_scene: int = Field(default=10, alias="maxEntitiesPerScene")
