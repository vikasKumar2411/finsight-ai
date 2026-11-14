
from langgraph.graph import StateGraph, START, END

from app.orchestration.state import InvestigationState

from app.orchestration.supervisor import (
    create_supervisor,
)

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
    max_supervisor_rounds: int = 2,
):
    """
    Build an investigation graph with a bounded
    supervisor feedback loop.
    """

    builder = StateGraph(InvestigationState)

    # Register nodes
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
        "supervisor",
        create_supervisor(max_supervisor_rounds),
    )

    builder.add_node(
        "finalize",
        finalize_investigation,
    )

    # Validate trusted plan identifiers
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

    builder.add_node("validate_plan", validate_plan)

    # Initial agent selection
    def route_initial_agents(
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
                "No executable capabilities selected"
            )

        return destinations

    # Supervisor routing decision
    def route_after_supervisor(
        state: InvestigationState,
    ) -> str:

        next_agent = state.get("next_agent")

        if next_agent == "entity_investigation":
            return "entity_investigation"

        return "finalize"

    # Start the workflow
    builder.add_edge(START, "validate_plan")

    builder.add_conditional_edges(
        "validate_plan",
        route_initial_agents,
        {
            "transaction_analysis": "transaction_analysis",
            "entity_investigation": "entity_investigation",
        },
    )

    # Collect evidence from whichever agents execute.
    builder.add_edge(
        "transaction_analysis",
        "evidence_evaluation",
    )

    builder.add_edge(
        "entity_investigation",
        "evidence_evaluation",
    )

    # Evaluate, then let the supervisor decide.
    builder.add_edge(
        "evidence_evaluation",
        "supervisor",
    )

    # Loop for more evidence or finish.
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "entity_investigation": "entity_investigation",
            "finalize": "finalize",
        },
    )

    builder.add_edge("finalize", END)

    return builder.compile()
