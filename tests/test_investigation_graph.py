
import asyncio

from app.orchestration.graph import build_investigation_graph
from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.telemetry import ToolTelemetry


def test_transaction_investigation():
    investigation_id = "INV-TEST-001"

    budget_manager = ExecutionBudgetManager()
    budget_manager.create_budget(
        investigation_id,
        max_tool_calls=5,
    )

    telemetry = ToolTelemetry()

    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget_manager,
        telemetry=telemetry,
    )

    graph = build_investigation_graph(gateway)

    initial_state = {
        "investigation_id": investigation_id,
        "alert_id": "ALERT001",
        "account_id": "ACC001",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
    }

    final_state = asyncio.run(graph.ainvoke(initial_state))

    assert final_state["status"] == "INITIAL_ANALYSIS_COMPLETED"

    assert len(final_state["transactions"]) > 0

    assert any(
        finding["transaction_id"] == "TX00489"
        and finding["amount"] == 45000
        for finding in final_state["findings"]
        if finding["type"] == "LARGE_TRANSFER"
    )

    assert budget_manager.get_budget(
        investigation_id
    ).tool_calls_used == 2

    events = telemetry.get_events()
    assert len(events) == 2
    assert all(event.status == "SUCCESS" for event in events)


def test_unknown_account_has_no_findings():
    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
    )

    graph = build_investigation_graph(gateway)

    initial_state = {
        "investigation_id": "INV-TEST-002",
        "alert_id": "TEST-UNKNOWN",
        "account_id": "ACC999",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
    }

    final_state = asyncio.run(graph.ainvoke(initial_state))

    assert final_state["transactions"] == []
    assert final_state["related_accounts"] == []
    assert final_state["findings"] == []
    assert final_state["status"] == "INITIAL_ANALYSIS_COMPLETED"
