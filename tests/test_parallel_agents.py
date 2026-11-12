
import asyncio

import pytest

from app.orchestration.graph import build_investigation_graph
from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import (
    ExecutionBudgetManager,
    BudgetExceededError,
)
from app.tools.telemetry import ToolTelemetry


def make_initial_state(investigation_id):
    return {
        "investigation_id": investigation_id,
        "alert_id": "ALERT001",
        "account_id": "ACC001",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
    }


def test_parallel_agents_share_state_and_budget():
    investigation_id = "INV-PARALLEL-001"

    budget_manager = ExecutionBudgetManager()
    budget_manager.create_budget(
        investigation_id,
        max_tool_calls=10,
    )

    telemetry = ToolTelemetry()

    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget_manager,
        telemetry=telemetry,
    )

    graph = build_investigation_graph(gateway)

    final_state = asyncio.run(
        graph.ainvoke(make_initial_state(investigation_id))
    )

    assert final_state["status"] == "INITIAL_ANALYSIS_COMPLETED"

    # Verify Transaction Agent findings.
    assert any(
        finding["type"] == "LARGE_TRANSFER"
        for finding in final_state["findings"]
    )

    # Verify Entity Agent findings.
    assert any(
        finding["type"] == "RELATED_ACCOUNT"
        for finding in final_state["findings"]
    )

    assert set(final_state["related_accounts"]) == {
        "ACC002",
        "ACC003",
    }

    # Two agents share one investigation budget.
    budget = budget_manager.get_budget(investigation_id)
    assert budget.tool_calls_used == 2

    # Both agents should produce telemetry events.
    events = telemetry.get_events()

    assert len(events) == 2
    assert all(event.status == "SUCCESS" for event in events)

    assert {event.agent_id for event in events} == {
        "transaction_agent",
        "entity_agent",
    }


def test_budget_exhaustion_blocks_parallel_work():
    investigation_id = "INV-PARALLEL-002"

    budget_manager = ExecutionBudgetManager()
    budget_manager.create_budget(
        investigation_id,
        max_tool_calls=1,
    )

    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget_manager,
    )

    graph = build_investigation_graph(gateway)

    with pytest.raises(BudgetExceededError):
        asyncio.run(
            graph.ainvoke(make_initial_state(investigation_id))
        )

    assert budget_manager.get_budget(
        investigation_id
    ).tool_calls_used == 1
