
import asyncio

from app.orchestration.graph import build_investigation_graph
from app.orchestration.supervisor import create_supervisor

from app.planning.schemas import InvestigationPlan

from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.telemetry import ToolTelemetry


def make_plan():
    return InvestigationPlan.model_validate({
        "investigation_id": "INV-SUP-001",
        "alert_id": "ALERT001",
        "investigation_questions": [
            "What happened in the flagged transaction?"
        ],
        "steps": [
            {
                "capability": "transaction_analysis",
                "objective": "Analyze flagged account transactions",
                "rationale": "Transaction evidence is required",
            }
        ],
    })


def make_state(account_id="ACC001"):
    return {
        "investigation_id": "INV-SUP-001",
        "alert_id": "ALERT001",
        "account_id": account_id,
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
        "assessment": None,
        "completed_capabilities": [],
        "supervisor_rounds": 0,
        "next_agent": None,
    }


def make_gateway():
    budget = ExecutionBudgetManager()
    budget.create_budget(
        "INV-SUP-001",
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


def test_supervisor_requests_missing_entity_evidence():
    supervisor = create_supervisor(max_rounds=2)

    state = make_state()
    state["completed_capabilities"] = [
        "transaction_analysis"
    ]
    state["findings"] = [
        {
            "type": "LARGE_TRANSFER",
            "transaction_id": "TX00489",
        }
    ]

    result = supervisor(state)

    assert result["supervisor_rounds"] == 1
    assert result["next_agent"] == "entity_investigation"


def test_supervisor_respects_max_rounds():
    supervisor = create_supervisor(max_rounds=1)

    state = make_state()
    state["completed_capabilities"] = [
        "transaction_analysis"
    ]
    state["findings"] = [
        {
            "type": "LARGE_TRANSFER",
            "transaction_id": "TX00489",
        }
    ]

    result = supervisor(state)

    assert result["supervisor_rounds"] == 1
    assert result["next_agent"] is None


def test_supervisor_loop_executes_second_agent():
    gateway, budget, telemetry = make_gateway()

    graph = build_investigation_graph(
        gateway=gateway,
        plan=make_plan(),
        max_supervisor_rounds=2,
    )

    result = asyncio.run(
        graph.ainvoke(make_state())
    )

    assert result["status"] == (
        "EVIDENCE_EVALUATION_COMPLETED"
    )

    # Transaction Agent executes first.
    # Entity Agent executes after supervisor review.
    assert result["completed_capabilities"] == [
        "transaction_analysis",
        "entity_investigation",
    ]

    assert result["supervisor_rounds"] == 2
    assert result["next_agent"] is None

    assert set(result["related_accounts"]) == {
        "ACC002",
        "ACC003",
    }

    assert result["assessment"]["decision"] == (
        "NEEDS_HUMAN_REVIEW"
    )

    assert budget.get_budget(
        "INV-SUP-001"
    ).tool_calls_used == 2

    assert {
        event.agent_id
        for event in telemetry.get_events()
    } == {
        "transaction_agent",
        "entity_agent",
    }


def test_supervisor_stops_when_no_signal_found():
    gateway, budget, telemetry = make_gateway()

    graph = build_investigation_graph(
        gateway=gateway,
        plan=make_plan(),
        max_supervisor_rounds=2,
    )

    result = asyncio.run(
        graph.ainvoke(make_state(account_id="ACC999"))
    )

    assert result["supervisor_rounds"] == 1
    assert result["next_agent"] is None

    assert result["completed_capabilities"] == [
        "transaction_analysis",
    ]

    assert budget.get_budget(
        "INV-SUP-001"
    ).tool_calls_used == 1

    assert len(telemetry.get_events()) == 1