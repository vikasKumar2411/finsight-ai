
from langgraph.graph import StateGraph, START, END

from app.orchestration.state import InvestigationState
from app.agents.transaction_agent import create_transaction_agent
from app.agents.entity_agent import create_entity_agent
from app.tools.gateway import ToolGateway


def finalize_investigation(
    state: InvestigationState,
) -> dict:
    """Run after both analysis branches complete."""

    return {
        "status": "INITIAL_ANALYSIS_COMPLETED",
    }


def build_investigation_graph(gateway: ToolGateway):
    builder = StateGraph(InvestigationState)

    builder.add_node(
        "transaction_analysis",
        create_transaction_agent(gateway),
    )

    builder.add_node(
        "entity_investigation",
        create_entity_agent(gateway),
    )

    builder.add_node(
        "finalize",
        finalize_investigation,
    )

    # Parallel fan-out
    builder.add_edge(START, "transaction_analysis")
    builder.add_edge(START, "entity_investigation")

    # Synchronization barrier:
    # wait for both branches before finalizing
    builder.add_edge(
        ["transaction_analysis", "entity_investigation"],
        "finalize",
    )

    builder.add_edge("finalize", END)

    return builder.compile()
