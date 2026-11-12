import pytest
from pydantic import ValidationError

from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry


@pytest.fixture
def gateway():
    registry = create_tool_registry()
    return ToolGateway(
        registry=registry,
        authorizer=ToolAuthorizer(),
    )


def test_execute_transaction_tool(gateway, execution_context):
    result = gateway.execute(
        "get_account_transactions",
        {"account_id": "ACC003"},
        context=execution_context,
    )

    assert result["account_id"] == "ACC003"
    assert result["count"] > 0
    assert len(result["transactions"]) == result["count"]


def test_execute_entity_tool(gateway, execution_context):
    result = gateway.execute(
        "get_related_accounts",
        {"account_id": "ACC004"},
        context=execution_context,
    )

    assert result["account_id"] == "ACC004"
    assert "ACC003" in result["related_accounts"]


def test_unknown_tool(gateway):
    with pytest.raises(ValueError, match="Unknown tool"):
        gateway.execute(
            "nonexistent_tool",
            {"account_id": "ACC003"},
            context=execution_context
        )


def test_invalid_arguments(gateway):
    with pytest.raises(ValidationError):
        gateway.execute(
            "get_account_transactions",
            {"account_id": "INVALID"},
            context=execution_context
        )


def test_extra_arguments_rejected(gateway):
    with pytest.raises(ValidationError):
        gateway.execute(
            "get_account_transactions",
            {
                "account_id": "ACC003",
                "admin_override": True,
            },
            context=execution_context
        )

from app.tools.security.authorization import (
    ExecutionContext,
    ToolAuthorizer,
    AuthorizationError,
)


@pytest.fixture
def execution_context():
    return ExecutionContext(
        user_id="analyst_001",
        agent_id="transaction_agent",
        investigation_id="INV-001",
        permissions=frozenset({
            "transactions:read",
            "accounts:read",
        }),
    )
