import pytest
from pydantic import BaseModel

from app.tools.registry import (
    ToolDefinition,
    ToolRegistry,
    create_tool_registry,
)


def test_registry_contains_expected_tools():
    registry = create_tool_registry()

    assert registry.list_tools() == [
        "get_account_transactions",
        "get_related_accounts",
    ]


def test_get_registered_tool():
    registry = create_tool_registry()

    tool = registry.get("get_account_transactions")

    assert tool is not None
    assert tool.name == "get_account_transactions"
    assert tool.required_permission == "transactions:read"
    assert tool.max_attempts == 3


def test_unknown_tool_returns_none():
    registry = create_tool_registry()

    assert registry.get("unknown_tool") is None


def test_duplicate_tool_registration_rejected():
    registry = create_tool_registry()
    existing_tool = registry.get("get_account_transactions")

    with pytest.raises(ValueError, match="already registered"):
        registry.register(existing_tool)


def test_registry_does_not_execute_tool():
    registry = ToolRegistry()

    def failing_handler():
        raise RuntimeError("Handler should not execute")

    registry.register(
        ToolDefinition(
            name="test_tool",
            description="Test tool",
            handler=failing_handler,
            input_schema=type("TestInput", (BaseModel,), {}),
            output_schema=type("TestOutput", (BaseModel,), {}),
            required_permission="test:read",
            timeout_seconds=5.0,
            max_attempts=2,
        )
    )

    assert registry.get("test_tool") is not None