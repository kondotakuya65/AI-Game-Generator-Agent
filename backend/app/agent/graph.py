"""Compile the game builder LangGraph (stub nodes)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import GameBuilderState


def build_game_builder_graph() -> StateGraph:
    graph = StateGraph(GameBuilderState)

    # Ask is checkpointed before the interrupt so resume never re-calls the LLM.
    graph.add_node("clarify_ask", nodes.clarify_ask_node)
    graph.add_node("clarify_gate", nodes.clarify_gate_node)
    graph.add_node("lock_spec", nodes.lock_spec_node)
    graph.add_node("design", nodes.design_node)
    graph.add_node("code", nodes.code_node)
    graph.add_node("test", nodes.test_node)
    graph.add_node("repair", nodes.repair_node)
    graph.add_node("deploy", nodes.deploy_node)

    graph.add_edge(START, "clarify_ask")
    graph.add_edge("clarify_ask", "clarify_gate")
    graph.add_edge("clarify_gate", "lock_spec")
    graph.add_edge("lock_spec", "design")
    graph.add_edge("design", "code")
    graph.add_edge("code", "test")
    graph.add_conditional_edges(
        "test",
        nodes.route_after_test,
        {
            "deploy": "deploy",
            "repair": "repair",
            "failed": END,
        },
    )
    graph.add_edge("repair", "test")
    graph.add_edge("deploy", END)
    return graph


def compile_game_builder_graph(*, checkpointer: MemorySaver | None = None):
    """Compile with an in-memory checkpointer (ready for later clarify pause)."""
    saver = checkpointer if checkpointer is not None else MemorySaver()
    return build_game_builder_graph().compile(checkpointer=saver)


@lru_cache
def get_compiled_graph():
    return compile_game_builder_graph()


def clear_graph_cache() -> None:
    get_compiled_graph.cache_clear()


__all__ = [
    "build_game_builder_graph",
    "clear_graph_cache",
    "compile_game_builder_graph",
    "get_compiled_graph",
]
