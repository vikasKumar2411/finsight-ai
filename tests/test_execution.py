
# tests/test_execution.py

import asyncio
import time

import pytest
from pydantic import BaseModel

from app.tools.gateway import ToolGateway
from app.tools.registry import ToolDefinition, ToolRegistry
from app.tools.security.authorization import (
    ExecutionContext,
    ToolAuthorizer,
)
from app.tools.execution.retry import (
    TransientToolError,
    ToolRetryExhaustedError,
)
from app.tools.execution.timeout import ToolTimeoutError


class SampleToolInput(BaseModel):
    value: int


class SampleToolOutput(BaseModel):
    result: int


@pytest.fixture
def context():
    return ExecutionContext(
        user_id="analyst_001",
        agent_id="test_agent",
        investigation_id="INV-001",
        permissions=frozenset({"test:execute"}),
    )


def make_gateway(handler, max_attempts=3, timeout=1.0):
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="test_tool",
            description="Test execution behavior",
            handler=handler,
            input_schema=SampleToolInput,
            output_schema=SampleToolOutput,
            required_permission="test:execute",
            timeout_seconds=timeout,
            max_attempts=max_attempts,
        )
    )

    return ToolGateway(
        registry=registry,
        authorizer=ToolAuthorizer(),
    )


def test_retry_succeeds_after_transient_failure(context):
    attempts = 0

    def flaky_tool(value: int):
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise TransientToolError("Temporary API failure")

        return {"result": value * 2}

    gateway = make_gateway(flaky_tool)

    result = gateway.execute(
        "test_tool",
        {"value": 5},
        context=context,
    )

    assert result == {"result": 10}
    assert attempts == 3


def test_retry_exhaustion(context):
    attempts = 0

    def failing_tool(value: int):
        nonlocal attempts
        attempts += 1
        raise TransientToolError("Service unavailable")

    gateway = make_gateway(
        failing_tool,
        max_attempts=2,
    )

    with pytest.raises(ToolRetryExhaustedError):
        gateway.execute(
            "test_tool",
            {"value": 5},
            context=context,
        )

    assert attempts == 2


def test_tool_timeout(context):
    def slow_tool(value: int):
        time.sleep(0.1)
        return {"result": value}

    gateway = make_gateway(
        slow_tool,
        max_attempts=1,
        timeout=0.01,
    )

    async def run_test():
        with pytest.raises(ToolTimeoutError):
            await gateway.execute_async(
                "test_tool",
                {"value": 5},
                context=context,
            )

    asyncio.run(run_test())


def test_non_retryable_error(context):
    attempts = 0

    def invalid_tool(value: int):
        nonlocal attempts
        attempts += 1
        raise ValueError("Invalid business operation")

    gateway = make_gateway(invalid_tool)

    with pytest.raises(ValueError):
        gateway.execute(
            "test_tool",
            {"value": 5},
            context=context,
        )

    assert attempts == 1
