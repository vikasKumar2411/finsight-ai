
import asyncio

from app.orchestration.graph import build_investigation_graph
from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.telemetry import ToolTelemetry


def test_transaction_investigation():
    investigation_id = "INV-TEST-001"

    # 1. Initialize execution budget
    budget_manager = ExecutionBudgetManager()
    budget_manager.create_budget(
        investigation_id,
        max_tool_calls=5,
    )

    # 2. Initialize telemetry
    telemetry = ToolTelemetry()

    # 3. Initialize Tool Gateway
    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget_manager,
        telemetry=telemetry,
    )

    # 4. Build LangGraph workflow
    graph = build_investigation_graph(gateway)

    # 5. Initial investigation state
    initial_state = {
        "investigation_id": investigation_id,
        "alert_id": "ALERT001",
        "account_id": "ACC001",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
        "assessment": None,
    }

    # 6. Execute investigation
    final_state = asyncio.run(
        graph.ainvoke(initial_state)
    )

    # 7. Verify investigation completion
    assert final_state["status"] == (
        "EVIDENCE_EVALUATION_COMPLETED"
    )

    # 8. Verify Evidence Evaluation Agent
    assert final_state["assessment"] is not None

    assert final_state["assessment"]["decision"] == (
        "NEEDS_HUMAN_REVIEW"
    )

    assert final_state["assessment"]["risk_level"] == (
        "UNDETERMINED"
    )

    # 9. Verify Transaction Analysis Agent
    assert len(final_state["transactions"]) > 0

    assert any(
        finding["transaction_id"] == "TX00489"
        and finding["amount"] == 45000
        for finding in final_state["findings"]
        if finding["type"] == "LARGE_TRANSFER"
    )

    # 10. Verify Entity Investigation Agent
    assert set(final_state["related_accounts"]) == {
        "ACC002",
        "ACC003",
    }

    assert any(
        finding["type"] == "RELATED_ACCOUNT"
        for finding in final_state["findings"]
    )

    # 11. Verify shared execution budget
    budget = budget_manager.get_budget(investigation_id)

    assert budget.tool_calls_used == 2
    assert budget.remaining == 3

    # 12. Verify tool execution telemetry
    events = telemetry.get_events()

    assert len(events) == 2

    assert all(
        event.status == "SUCCESS"
        for event in events
    )

    assert {
        event.agent_id
        for event in events
    } == {
        "transaction_agent",
        "entity_agent",
    }


def test_unknown_account_has_no_findings():

    # 1. Initialize Tool Gateway
    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
    )

    # 2. Build LangGraph workflow
    graph = build_investigation_graph(gateway)

    # 3. Initial state for unknown account
    initial_state = {
        "investigation_id": "INV-TEST-002",
        "alert_id": "TEST-UNKNOWN",
        "account_id": "ACC999",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
        "assessment": None,
    }

    # 4. Execute investigation
    final_state = asyncio.run(
        graph.ainvoke(initial_state)
    )

    # 5. Verify no transaction or relationship findings
    assert final_state["transactions"] == []
    assert final_state["related_accounts"] == []
    assert final_state["findings"] == []

    # 6. Verify Evidence Evaluation Agent
    assert final_state["assessment"] is not None

    assert final_state["assessment"]["decision"] == (
        "NO_THRESHOLD_FLAGS"
    )

    assert final_state["assessment"]["risk_level"] == (
        "UNDETERMINED"
    )

    # 7. Verify investigation completion
    assert final_state["status"] == (
        "EVIDENCE_EVALUATION_COMPLETED"
    )
