
import asyncio

import pytest

from app.orchestration.graph import build_investigation_graph
from app.planning.schemas import InvestigationPlan

from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.telemetry import ToolTelemetry


INVESTIGATION_ID = "INV-ROUTING-001"
ALERT_ID = "ALERT001"


def make_plan(capabilities):
    return InvestigationPlan.model_validate({
        "investigation_id": INVESTIGATION_ID,
        "alert_id": ALERT_ID,
        "investigation_questions": [
            "What evidence is available for the alert?"
        ],
        "steps": [
            {
                "capability": capability,
                "objective": (
                    "Collect relevant investigation evidence"
                ),
                "rationale": (
                    "This capability supports the investigation"
                ),
            }
            for capability in capabilities
        ],
    })


def make_state():
    return {
        "investigation_id": INVESTIGATION_ID,
        "alert_id": ALERT_ID,
        "account_id": "ACC001",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
        "assessment": None,
    }


def make_gateway():
    budget = ExecutionBudgetManager()
    budget.create_budget(
        INVESTIGATION_ID,
        max_tool_calls=10,
    )

    telemetry = ToolTelemetry()

    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget,
        telemetry=telemetry,
    )

    return gateway, budget, telemetry


def test_transaction_only_routing():
    plan = make_plan(["transaction_analysis"])
    gateway, budget, telemetry = make_gateway()

    graph = build_investigation_graph(gateway, plan)

    result = asyncio.run(graph.ainvoke(make_state()))

    assert result["status"] == "EVIDENCE_EVALUATION_COMPLETED"
    assert len(result["transactions"]) > 0
    assert result["related_accounts"] == []

    assert budget.get_budget(
        INVESTIGATION_ID
    ).tool_calls_used == 1

    assert {
        event.agent_id
        for event in telemetry.get_events()
    } == {"transaction_agent"}


def test_entity_only_routing():
    plan = make_plan(["entity_investigation"])
    gateway, budget, telemetry = make_gateway()

    graph = build_investigation_graph(gateway, plan)

    result = asyncio.run(graph.ainvoke(make_state()))

    assert result["status"] == "EVIDENCE_EVALUATION_COMPLETED"
    assert result["transactions"] == []
    assert set(result["related_accounts"]) == {
        "ACC002",
        "ACC003",
    }

    assert budget.get_budget(
        INVESTIGATION_ID
    ).tool_calls_used == 1

    assert {
        event.agent_id
        for event in telemetry.get_events()
    } == {"entity_agent"}


def test_both_agents_routing():
    plan = make_plan([
        "transaction_analysis",
        "entity_investigation",
    ])

    gateway, budget, telemetry = make_gateway()
    graph = build_investigation_graph(gateway, plan)

    result = asyncio.run(graph.ainvoke(make_state()))

    assert result["status"] == "EVIDENCE_EVALUATION_COMPLETED"
    assert len(result["transactions"]) > 0
    assert len(result["related_accounts"]) == 2

    assert budget.get_budget(
        INVESTIGATION_ID
    ).tool_calls_used == 2

    assert {
        event.agent_id
        for event in telemetry.get_events()
    } == {
        "transaction_agent",
        "entity_agent",
    }


def test_mismatched_investigation_rejected():
    plan = make_plan(["transaction_analysis"])
    gateway, budget, telemetry = make_gateway()

    graph = build_investigation_graph(gateway, plan)

    state = make_state()
    state["investigation_id"] = "INV-OTHER"

    with pytest.raises(ValueError, match="Investigation ID"):
        asyncio.run(graph.ainvoke(state))

    assert budget.get_budget(
        INVESTIGATION_ID
    ).tool_calls_used == 0

    assert telemetry.get_events() == []


def test_mismatched_alert_rejected():
    plan = make_plan(["transaction_analysis"])
    gateway, budget, telemetry = make_gateway()

    graph = build_investigation_graph(gateway, plan)

    state = make_state()
    state["alert_id"] = "ALERT-OTHER"

    with pytest.raises(ValueError, match="Alert ID"):
        asyncio.run(graph.ainvoke(state))

    assert budget.get_budget(
        INVESTIGATION_ID
    ).tool_calls_used == 0

    assert telemetry.get_events() == []
