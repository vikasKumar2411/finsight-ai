
from langgraph.graph import StateGraph, START, END

from app.orchestration.state import InvestigationState

from app.agents.transaction_agent import (
    create_transaction_agent,
)

from app.agents.entity_agent import (
    create_entity_agent,
)

from app.agents.evidence_evaluator import (
    evaluate_evidence,
)

from app.tools.gateway import ToolGateway


def finalize_investigation(
    state: InvestigationState,
) -> dict:

    return {
        "status": "EVIDENCE_EVALUATION_COMPLETED",
    }


def build_investigation_graph(
    gateway: ToolGateway,
):
    builder = StateGraph(InvestigationState)

    # 1. Parallel investigation agents
    builder.add_node(
        "transaction_analysis",
        create_transaction_agent(gateway),
    )

    builder.add_node(
        "entity_investigation",
        create_entity_agent(gateway),
    )

    # 2. Evidence evaluation
    builder.add_node(
        "evidence_evaluation",
        evaluate_evidence,
    )

    # 3. Finalization
    builder.add_node(
        "finalize",
        finalize_investigation,
    )

    # Parallel fan-out
    builder.add_edge(
        START,
        "transaction_analysis",
    )

    builder.add_edge(
        START,
        "entity_investigation",
    )

    # Wait for both agents to complete.
    builder.add_edge(
        [
            "transaction_analysis",
            "entity_investigation",
        ],
        "evidence_evaluation",
    )

    # Evaluate before finalizing.
    builder.add_edge(
        "evidence_evaluation",
        "finalize",
    )

    builder.add_edge(
        "finalize",
        END,
    )

    return builder.compile()
