# -*- coding: utf-8 -*-
"""Agent 上下文组装：StoryAgentContext。"""
from __future__ import annotations

from typing import Any, Literal, Optional

from keeper.base.coc_model.model import (
    AgentContextOptions,
    ClueCard,
    Visibility,
)
from keeper.base.coc_model.story_module import StoryModule
from keeper.base.coc_model.story_session import StorySession

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
