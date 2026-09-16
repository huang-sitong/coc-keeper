# -*- coding: utf-8 -*-
"""模组包：StoryModule。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import PrivateAttr

from keeper.base.creature import Creature
from keeper.base.story.model import (
    ClueCard,
    HandoutCard,
    ItemCard,
    NpcCard,
    Secret,
    StoryModuleData,
    StoryValidation,
)
from keeper.base.story.story_graph import StoryGraph

class StoryModule(StoryModuleData):
    """模组包：加载全部素材，提供索引与按需检索。"""

    graph: StoryGraph

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
