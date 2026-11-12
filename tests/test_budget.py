
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.tools.execution.budget import (
    ExecutionBudgetManager,
    BudgetExceededError,
    BudgetNotFoundError,
)
from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import (
    AuthorizationError,
    ExecutionContext,
    ToolAuthorizer,
)


@pytest.fixture
def manager():
    budget_manager = ExecutionBudgetManager()
    budget_manager.create_budget(
        investigation_id="INV-001",
        max_tool_calls=3,
    )
    return budget_manager


@pytest.fixture
def context():
    return ExecutionContext(
        user_id="analyst_001",
        agent_id="transaction_agent",
        investigation_id="INV-001",
        permissions=frozenset({
            "transactions:read",
            "accounts:read",
        }),
    )


def test_initial_budget(manager):
    budget = manager.get_budget("INV-001")

    assert budget.max_tool_calls == 3
    assert budget.tool_calls_used == 0
    assert budget.remaining == 3


def test_budget_reservation(manager):
    remaining = manager.reserve_call("INV-001")

    assert remaining == 2

    budget = manager.get_budget("INV-001")
    assert budget.tool_calls_used == 1


def test_budget_exhaustion(manager):
    for _ in range(3):
        manager.reserve_call("INV-001")

    with pytest.raises(BudgetExceededError):
        manager.reserve_call("INV-001")

    assert manager.get_budget("INV-001").tool_calls_used == 3


def test_missing_budget(manager):
    with pytest.raises(BudgetNotFoundError):
        manager.reserve_call("UNKNOWN")


def test_duplicate_budget_rejected(manager):
    with pytest.raises(ValueError, match="already exists"):
        manager.create_budget("INV-001")


def test_gateway_consumes_budget(manager, context):
    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=manager,
    )

    result = gateway.execute(
        "get_account_transactions",
        {"account_id": "ACC003"},
        context=context,
    )

    assert result["account_id"] == "ACC003"
    assert manager.get_budget("INV-001").remaining == 2


def test_multiple_agents_share_budget(manager, context):
    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=manager,
    )

    entity_context = ExecutionContext(
        user_id=context.user_id,
        agent_id="entity_agent",
        investigation_id=context.investigation_id,
        permissions=context.permissions,
    )

    gateway.execute(
        "get_account_transactions",
        {"account_id": "ACC003"},
        context=context,
    )

    gateway.execute(
        "get_related_accounts",
        {"account_id": "ACC004"},
        context=entity_context,
    )

    assert manager.get_budget("INV-001").remaining == 1


def test_unauthorized_call_does_not_consume_budget(manager):
    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=manager,
    )

    denied_context = ExecutionContext(
        user_id="analyst_002",
        agent_id="transaction_agent",
        investigation_id="INV-001",
        permissions=frozenset(),
    )

    with pytest.raises(AuthorizationError):
        gateway.execute(
            "get_account_transactions",
            {"account_id": "ACC003"},
            context=denied_context,
        )

    assert manager.get_budget("INV-001").remaining == 3


def test_concurrent_reservations_do_not_exceed_limit():
    manager = ExecutionBudgetManager()
    manager.create_budget("INV-002", max_tool_calls=10)

    def attempt_reservation(_):
        try:
            manager.reserve_call("INV-002")
            return True
        except BudgetExceededError:
            return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(attempt_reservation, range(50)))

    assert sum(results) == 10
    assert manager.get_budget("INV-002").tool_calls_used == 10


def test_budget_snapshot_cannot_change_internal_state(manager):
    snapshot = manager.get_budget("INV-001")
    snapshot.tool_calls_used = 100

    assert manager.get_budget("INV-001").tool_calls_used == 0
