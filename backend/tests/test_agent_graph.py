"""Stub LangGraph happy-path + repair-routing tests."""

from __future__ import annotations

from typing import Any

from app.agent.graph import compile_game_builder_graph
from app.agent.nodes import route_after_test
from app.agent.resume import resume_with_answers
from app.agent.state import NODE_ORDER, GameBuilderState, initial_state

FIXTURE_ANSWERS = {
    "twist": "near-miss recharges shields",
    "difficulty": "standard",
    "win": "clear 5 waves",
    "art": "minimal geometric",
}


def test_stub_happy_path_invoke():
    graph = compile_game_builder_graph()
    config = {"configurable": {"thread_id": "stub-happy-1"}}
    result = graph.invoke(
        initial_state(
            "Make a new game like a space shooter",
            run_id="stub-1",
            answers=FIXTURE_ANSWERS,
        ),
        config=config,
    )

    assert result["status"] == "completed"
    assert result["spec_locked"] is True
    assert result["test_passed"] is True
    assert result["play_url"] == "/play/stub-1"
    assert result["gamespec"]["genre"] == "shooter"
    assert "near-miss" in result["gamespec"]["twist"]
    assert result.get("error") is None

    thought_nodes = [t["node"] for t in result["trace"] if t.get("kind") == "thought"]
    assert thought_nodes == list(NODE_ORDER)

    kinds = {t["kind"] for t in result["trace"]}
    assert {"thought", "action", "observation"}.issubset(kinds)
    assert "repair" not in thought_nodes


def test_clarify_interrupt_then_confirm_locks_spec():
    graph = compile_game_builder_graph()
    config = {"configurable": {"thread_id": "clarify-hitl-1"}}
    paused = graph.invoke(
        initial_state("Make a space shooter", run_id="clarify-1"),
        config=config,
    )
    assert paused.get("__interrupt__")
    interrupt_val = paused["__interrupt__"][0].value
    assert interrupt_val["type"] == "clarify"
    assert len(interrupt_val["questions"]) >= 3

    result = graph.invoke(resume_with_answers(FIXTURE_ANSWERS), config=config)
    assert not result.get("__interrupt__")
    assert result["spec_locked"] is True
    assert result["gamespec"]["title"]
    assert result["status"] == "completed"
    assert result["play_url"] == "/play/clarify-1"


def test_route_after_test_branches():
    passed: GameBuilderState = {
        "run_id": "r",
        "prompt": "p",
        "questions": [],
        "acceptance_tests": [],
        "messages": [],
        "trace": [],
        "test_passed": True,
        "repair_count": 0,
        "repair_budget": 3,
    }
    assert route_after_test(passed) == "deploy"

    fail_repair: GameBuilderState = {
        **passed,
        "test_passed": False,
        "repair_count": 1,
        "repair_budget": 3,
    }
    assert route_after_test(fail_repair) == "repair"

    fail_exhausted: GameBuilderState = {
        **passed,
        "test_passed": False,
        "repair_count": 3,
        "repair_budget": 3,
    }
    assert route_after_test(fail_exhausted) == "failed"


def test_repair_loop_then_deploy(monkeypatch):
    """First test fails → repair → second test passes → deploy."""
    from app.agent import nodes

    calls = {"n": 0}

    def flaky_test(state: GameBuilderState) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            report = {"passed": False, "items": [], "summary": "stub fail"}
            return {
                "status": "testing",
                "test_report": report,
                "test_passed": False,
                "messages": ["test: stub fail"],
                "trace": [
                    {
                        "kind": "thought",
                        "node": "test",
                        "message": "fail once",
                    }
                ],
            }
        report = {"passed": True, "items": [], "summary": "stub pass"}
        return {
            "status": "testing",
            "test_report": report,
            "test_passed": True,
            "messages": ["test: stub pass"],
            "trace": [
                {
                    "kind": "thought",
                    "node": "test",
                    "message": "pass on retry",
                }
            ],
        }

    monkeypatch.setattr(nodes, "test_node", flaky_test)
    graph = compile_game_builder_graph()
    result = graph.invoke(
        initial_state(
            "space shooter",
            run_id="repair-1",
            repair_budget=3,
            answers=FIXTURE_ANSWERS,
        ),
        config={"configurable": {"thread_id": "stub-repair-1"}},
    )

    assert result["status"] == "completed"
    assert result["test_passed"] is True
    assert result["repair_count"] == 1
    assert result["play_url"] == "/play/repair-1"
    thought_nodes = [t["node"] for t in result["trace"] if t.get("kind") == "thought"]
    assert "repair" in thought_nodes
    assert thought_nodes.count("test") >= 2
