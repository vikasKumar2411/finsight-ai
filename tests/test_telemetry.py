import pytest
from pydantic import BaseModel

from app.tools.gateway import ToolGateway
from app.tools.registry import ToolDefinition, ToolRegistry
from app.tools.security.authorization import (
    ExecutionContext,
    ToolAuthorizer,
)
from app.tools.telemetry import ToolTelemetry
from app.tools.execution.retry import (
    TransientToolError,
    ToolRetryExhaustedError,
)


class SampleInput(BaseModel):
    value: int


class SampleOutput(BaseModel):
    result: int


@pytest.fixture
def context():
    return ExecutionContext(
        user_id="analyst_001",
        agent_id="transaction_agent",
        investigation_id="INV-001",
        permissions=frozenset({"test:execute"}),
    )


def make_gateway(handler, max_attempts=3):
    registry = ToolRegistry()
    telemetry = ToolTelemetry()

    registry.register(
        ToolDefinition(
            name="sample_tool",
            description="A sample execution tool",
            handler=handler,
            input_schema=SampleInput,
            output_schema=SampleOutput,
            required_permission="test:execute",
            timeout_seconds=2.0,
            max_attempts=max_attempts,
        )
    )

    gateway = ToolGateway(
        registry=registry,
        authorizer=ToolAuthorizer(),
        telemetry=telemetry,
    )

    return gateway, telemetry


def test_successful_execution_telemetry(context):
    def handler(value: int):
        return {"result": value * 2}

    gateway, telemetry = make_gateway(handler)

    result = gateway.execute(
        "sample_tool",
        {"value": 5},
        context=context,
    )

    assert result == {"result": 10}

    events = telemetry.get_events()

    assert len(events) == 1
    assert events[0].status == "SUCCESS"
    assert events[0].attempt_count == 1
    assert events[0].investigation_id == "INV-001"
    assert events[0].agent_id == "transaction_agent"
    assert events[0].tool_name == "sample_tool"
    assert events[0].duration_ms >= 0
    assert events[0].tool_call_id


def test_retry_attempts_recorded(context):
    attempts = 0

    def handler(value: int):
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise TransientToolError("Temporary failure")

        return {"result": value}

    gateway, telemetry = make_gateway(handler)

    gateway.execute(
        "sample_tool",
        {"value": 10},
        context=context,
    )

    event = telemetry.get_events()[0]

    assert event.status == "SUCCESS"
    assert event.attempt_count == 3
    assert event.error_type is None


def test_failure_telemetry(context):
    def handler(value: int):
        raise TransientToolError("Service unavailable")

    gateway, telemetry = make_gateway(
        handler,
        max_attempts=2,
    )

    with pytest.raises(ToolRetryExhaustedError):
        gateway.execute(
            "sample_tool",
            {"value": 5},
            context=context,
        )

    event = telemetry.get_events()[0]

    assert event.status == "FAILED"
    assert event.attempt_count == 2
    assert event.error_type == "ToolRetryExhaustedError"


def test_telemetry_returns_snapshot(context):
    def handler(value: int):
        return {"result": value}

    gateway, telemetry = make_gateway(handler)

    gateway.execute(
        "sample_tool",
        {"value": 5},
        context=context,
    )

    events = telemetry.get_events()
    events.clear()

    assert len(telemetry.get_events()) == 1
