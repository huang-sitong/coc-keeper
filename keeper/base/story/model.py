# -*- coding: utf-8 -*-
"""COC 故事流程图 / 模组素材：纯数据模型。

无自定义方法的类集中在此，供各功能模块复用。
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from keeper.base.investigator import (
    AttributeName,
    Attributes,
    Difficulty,
    SkillGroups,
    WeaponList,
)




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
    graph: StoryGraphData
    npcs: list[NpcCard] = Field(default_factory=list)
    creatures: list[Creature] = Field(default_factory=list)
    items: list[ItemCard] = Field(default_factory=list)
    clues: list[ClueCard] = Field(default_factory=list)
    handouts: list[HandoutCard] = Field(default_factory=list)
    secrets: list[Secret] = Field(default_factory=list)



# ==================== Agent 上下文组装 ====================


class AgentContextOptions(StoryBaseModel):
    """Agent 上下文组装选项。"""

    include_keeper_info: bool = Field(default=True, alias="includeKeeperInfo")
    max_entities_per_scene: int = Field(default=10, alias="maxEntitiesPerScene")
