
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

from app.planning.schemas import (
    InvestigationPlan,
    InvestigationCapability,
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
    plan: InvestigationPlan | None = None,
):
    """
    Build a plan-driven investigation graph.

    When plan is None, retain the original
    two-agent behavior for compatibility.
    """

    builder = StateGraph(InvestigationState)

    # 1. Register investigation agents
    builder.add_node(
        "transaction_analysis",
        create_transaction_agent(gateway),
    )

    builder.add_node(
        "entity_investigation",
        create_entity_agent(gateway),
    )

    builder.add_node(
        "evidence_evaluation",
        evaluate_evidence,
    )

    builder.add_node(
        "finalize",
        finalize_investigation,
    )

    # 2. Validate the plan against trusted graph input
    def validate_plan(state: InvestigationState) -> dict:
        if plan is not None:
            if plan.investigation_id != state["investigation_id"]:
                raise ValueError(
                    "Investigation ID does not match plan"
                )

            if plan.alert_id != state["alert_id"]:
                raise ValueError(
                    "Alert ID does not match plan"
                )

        return {"status": "PLAN_VALIDATED"}

    builder.add_node(
        "validate_plan",
        validate_plan,
    )

    # 3. Decide which agents execute
    def route_agents(
        state: InvestigationState,
    ) -> list[str]:

        if plan is None:
            return [
                "transaction_analysis",
                "entity_investigation",
            ]

        selected = {
            step.capability
            for step in plan.steps
        }

        destinations = []

        if (
            InvestigationCapability.TRANSACTION_ANALYSIS
            in selected
        ):
            destinations.append("transaction_analysis")

        if (
            InvestigationCapability.ENTITY_INVESTIGATION
            in selected
        ):
            destinations.append("entity_investigation")

        if not destinations:
            raise ValueError(
                "Investigation plan selected no executable agents"
            )

        return destinations

    # 4. Start with plan validation
    builder.add_edge(START, "validate_plan")

    # 5. Route to selected agents
    builder.add_conditional_edges(
        "validate_plan",
        route_agents,
        {
            "transaction_analysis": "transaction_analysis",
            "entity_investigation": "entity_investigation",
        },
    )

    # 6. Both possible branches lead to evaluation
    builder.add_edge(
        "transaction_analysis",
        "evidence_evaluation",
    )

    builder.add_edge(
        "entity_investigation",
        "evidence_evaluation",
    )

    # 7. Finalize
    builder.add_edge(
        "evidence_evaluation",
        "finalize",
    )

    builder.add_edge("finalize", END)

    return builder.compile()
