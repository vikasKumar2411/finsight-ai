import pytest

from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import (
    AuthorizationError,
    ExecutionContext,
    ToolAuthorizer,
)


@pytest.fixture
def gateway():
    return ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
    )


def test_authorized_tool_execution(gateway):
    context = ExecutionContext(
        user_id="analyst_001",
        agent_id="transaction_agent",
        investigation_id="INV-001",
        permissions=frozenset({"transactions:read"}),
    )

    result = gateway.execute(
        "get_account_transactions",
        {"account_id": "ACC003"},
        context=context,
    )

    assert result["count"] > 0


def test_unauthorized_tool_execution(gateway):
    context = ExecutionContext(
        user_id="analyst_002",
        agent_id="transaction_agent",
        investigation_id="INV-002",
        permissions=frozenset({"accounts:read"}),
    )

    with pytest.raises(AuthorizationError):
        gateway.execute(
            "get_account_transactions",
            {"account_id": "ACC003"},
            context=context,
        )


def test_no_permissions(gateway):
    context = ExecutionContext(
        user_id="analyst_003",
        agent_id="entity_agent",
        investigation_id="INV-003",
        permissions=frozenset(),
    )

    with pytest.raises(AuthorizationError):
        gateway.execute(
            "get_related_accounts",
            {"account_id": "ACC004"},
            context=context,
        )