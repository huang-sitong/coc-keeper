# -*- coding: utf-8 -*-
"""故事流程图 / 模组素材模型测试。"""
import json
from pathlib import Path

from keeper.base.story import (
    EdgeKind,
    FlagCondition,
    StoryAgentContext,
    StoryGraph,
    StoryModule,
    StoryNode,
    StoryNodeType,
    StorySession,
    StoryEdge,
    SetFlagAction,
)


def load_graph() -> StoryGraph:
    path = Path(__file__).resolve().parents[1] / ".docs" / "HauntingStoryGraph.json"
    return StoryGraph.from_json(json.loads(path.read_text(encoding="utf-8")))


def load_module() -> StoryModule:
    path = Path(__file__).resolve().parents[1] / ".docs" / "HauntingStoryModule.json"
    return StoryModule.from_json(json.loads(path.read_text(encoding="utf-8")))


def test_load_haunting_graph():
    graph = load_graph()
    assert len(graph.nodes) == 31
    assert len(graph.edges) == 67
    assert graph.validate().ok is True
    assert graph.get_start_node().id == "start"


def test_load_haunting_module():
    module = load_module()
    assert module.validate().ok is True
    assert module.get_npc("npc_knott") is not None
    assert module.get_creature("creature_corbitt") is not None
    assert module.get_item("item_magic_dagger") is not None
    assert module.get_clue("clue_handout2") is not None
    assert len(module.get_entities_for_node("newspaper_success")["npcs"]) >= 1


def test_story_graph_crud():
    graph = StoryGraph(
        id="g",
        title="test",
        start_node_id="start",
        nodes=[StoryNode(id="start", type=StoryNodeType.START, title="开始", text="开始")],
        edges=[],
    )
    end = StoryNode(id="end", type=StoryNodeType.END, title="结束", text="结束")
    assert graph.add_node(end) is True
    assert graph.add_node(end) is False

    edge = StoryEdge(
        id="e1",
        from_node="start",
        to="end",
        kind=EdgeKind.AUTO,
    )
    assert graph.add_edge(edge) is True
    assert graph.add_edge(edge) is False
    assert graph.remove_edge("e1") is True
    assert graph.remove_node("end") is True
    assert graph.validate().ok is True


def test_story_session_auto_and_choice():
    graph = StoryGraph(
        id="g",
        title="test",
        start_node_id="start",
        nodes=[
            StoryNode(id="start", type=StoryNodeType.START, title="开始", text="开始"),
            StoryNode(id="hub", type=StoryNodeType.SCENE, title="选择", text="选择"),
            StoryNode(id="end", type=StoryNodeType.END, title="结束", text="结束"),
        ],
        edges=[
            StoryEdge(id="e1", from_node="start", to="hub", kind=EdgeKind.AUTO),
            StoryEdge(id="e2", from_node="hub", to="end", kind=EdgeKind.CHOICE, label="结束"),
        ],
    )
    session = StorySession(graph)
    assert session.start().id == "start"
    assert session.advance().id == "hub"
    options = session.get_options()
    assert len(options) == 1
    assert options[0].label == "结束"
    assert session.choose(options[0].edge_id).id == "end"
    assert session.is_finished() is True


def test_story_session_condition_and_actions():
    graph = StoryGraph(
        id="g",
        title="test",
        start_node_id="start",
        nodes=[
            StoryNode(id="start", type=StoryNodeType.START, title="开始", text="开始"),
            StoryNode(
                id="locked",
                type=StoryNodeType.SCENE,
                title="锁",
                text="锁",
                enter_actions=[SetFlagAction(kind="setFlag", flag="visited_locked", value=True)],
            ),
            StoryNode(id="end", type=StoryNodeType.END, title="结束", text="结束"),
        ],
        edges=[
            StoryEdge(
                id="e1",
                from_node="start",
                to="locked",
                kind=EdgeKind.CONDITION,
                condition=FlagCondition(kind="flag", flag="has_key", op="exists"),
            ),
            StoryEdge(
                id="e2",
                from_node="start",
                to="end",
                kind=EdgeKind.CHOICE,
                label="直接结束",
            ),
        ],
    )
    session = StorySession(graph)
    # 没有 key 时，条件边不可走
    assert session.get_available_edges()[0].id == "e2"
    session.set_flag("has_key", True)
    available = {e.id for e in session.get_available_edges()}
    assert available == {"e1", "e2"}
    session.choose("e1")
    assert session.get_flag("visited_locked") is True


def test_story_session_snapshot_restore():
    graph = load_graph()
    session = StorySession(graph)
    session.start()
    session.advance()
    session.set_flag("test", 1)
    snap = session.snapshot()
    restored = StorySession(graph)
    restored.restore(snap)
    assert restored.current_node_id == session.current_node_id
    assert restored.get_flag("test") == 1


def test_story_agent_context_build_prompt():
    module = load_module()
    graph = module.graph
    session = StorySession(graph)
    session.start()
    session.advance()
    context = StoryAgentContext(module, session)
    prompt = context.build_prompt()
    assert "《鬼屋》" in prompt
    assert "当前场景" in prompt
    assert "去波士顿环球报社查旧报纸" in prompt
    assert context.get_revealed_clues() == []
    session.set_flag("newspaper_clue", True)
    assert any(c.id == "clue_handout2" for c in context.get_revealed_clues())


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__]))


def test_creature_profile_detailed():
    module = load_module()
    corbitt = module.get_creature("creature_corbitt")
    assert corbitt is not None
    assert corbitt.attributes.str == 90
    assert corbitt.hp == 16
    assert corbitt.mp == 18
    assert corbitt.db == "+1D4"
    assert corbitt.build == 1
    assert corbitt.move == 8
    skill_names = {
        s.name
        for group in corbitt.skills.all_group_lists()
        for s in group
    }
    assert "斗殴" in skill_names
    assert "克苏鲁神话" in skill_names
    assert any(w.name == "浮空魔法匕首" for w in corbitt.weapons.items)


def test_creature_package_and_method_interfaces():
    from keeper.base.investigator import Skill, SkillGroup, Weapon
    from keeper.base.creature import Creature
    from keeper.base.creature.creature import Creature as CreatureFromCore
    from keeper.base.module_base import ModuleBaseModel

    assert Creature is CreatureFromCore
    assert issubclass(Creature, ModuleBaseModel)

    module = load_module()
    corbitt = module.get_creature("creature_corbitt")
    assert corbitt is not None
    assert corbitt.get_attribute("str") == 90
    assert corbitt.get_skill_by_name("斗殴").total == 50
    assert corbitt.check_skill("fight", rng=lambda: 0.01).success is True
    assert corbitt.check_attribute("str", rng=lambda: 0.01).success is True

    attack = corbitt.attack_by_skill("fight", rng=lambda: 0.01)
    assert attack is not None and attack.hit is True
    assert attack.weapon_id == "corbitt_fist"
    assert attack.damage_roll == 2  # 1D3+1D4 with rng=0.01 -> 1+1

    assert corbitt.get_armor_expression() == "2D6"
    assert corbitt.roll_armor(rng=lambda: 0.25) == 4
    assert corbitt.resolve_armor(rng=lambda: 0.25).value == 4

    dagger = module.get_creature("creature_floating_dagger")
    assert dagger.get_sanity_loss_expression(success=True) == "1"
    assert dagger.get_sanity_loss_expression(success=False) == "1D4"
    assert dagger.roll_sanity_loss(success=True, rng=lambda: 0.5) == 1
    assert dagger.resolve_sanity_loss(success=False, rng=lambda: 0.5).loss == 3


def test_creature_attack_and_damage_methods():
    from keeper.base.investigator import Skill, SkillGroup, Weapon
    from keeper.base.creature import Creature

    monster = Creature(
        id="monster",
        name="测试怪物",
        hp=10,
        attributes={"str": 50, "con": 50},
    )
    assert monster.get_hp_max() == 10

    monster.skills.add_skill(SkillGroup.COMBAT, Skill(id="claw", name="爪击", base=60))
    monster.weapons.add_weapon(Weapon(id="claw", name="爪", skill_id="claw", damage="1D6", num=""))

    attack = monster.attack_by_skill("claw", rng=lambda: 0.01)
    assert attack is not None and attack.hit is True
    assert attack.attack is not None
    assert attack.attack.damage == "1D6"
    assert attack.damage_roll == 1

    damage = monster.take_damage(6, rng=lambda: 0.01)
    assert monster.hp == 4
    assert damage.major_wound is True
    assert damage.con_check is not None and damage.con_check.success is True
    assert damage.dead is False
    assert monster.is_alive() is True

    damage = monster.take_damage(20, rng=lambda: 0.01)
    assert monster.hp == -10
    assert monster.is_dead() is True
    assert damage.dead is True
