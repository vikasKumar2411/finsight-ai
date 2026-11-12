
import asyncio
import time
from typing import Any
from uuid import uuid4

from app.tools.registry import ToolRegistry
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.execution.retry import (
    TransientToolError,
    execute_with_retry,
)
from app.tools.execution.timeout import (
    ToolTimeoutError,
    execute_with_timeout,
)
from app.tools.security.authorization import (
    ExecutionContext,
    ToolAuthorizer,
)
from app.tools.telemetry import (
    ToolExecutionEvent,
    ToolTelemetry,
    utc_timestamp,
)


class ToolGateway:

    def __init__(
        self,
        registry: ToolRegistry,
        authorizer: ToolAuthorizer,
        budget_manager: ExecutionBudgetManager | None = None,
        telemetry: ToolTelemetry | None = None,
    ):
        self.registry = registry
        self.authorizer = authorizer
        self.budget_manager = budget_manager
        self.telemetry = (
            telemetry if telemetry is not None
            else ToolTelemetry()
        )

    async def execute_async(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:

        # 1. Registry lookup
        tool = self.registry.get(tool_name)

        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        # 2. Input validation
        validated_input = tool.input_schema.model_validate(
            arguments
        )

        # 3. Authorization
        self.authorizer.authorize(
            required_permission=tool.required_permission,
            context=context,
        )

        # 4. Budget reservation
        if self.budget_manager is not None:
            self.budget_manager.reserve_call(
                context.investigation_id
            )

        # 5. Initialize execution tracking
        tool_call_id = str(uuid4())
        start_time = time.perf_counter()
        attempts = 0
        status = "FAILED"
        error_type = None

        async def execute_attempt():
            nonlocal attempts
            attempts += 1

            return await execute_with_timeout(
                handler=tool.handler,
                arguments=validated_input.model_dump(),
                timeout_seconds=tool.timeout_seconds,
            )

        try:
            # 6. Execute with retries
            result = await execute_with_retry(
                operation=execute_attempt,
                max_attempts=tool.max_attempts,
                retryable_exceptions=(TransientToolError,),
            )

            # 7. Adapt existing tool outputs
            if tool_name == "get_account_transactions":
                result = {
                    "account_id": validated_input.account_id,
                    "transactions": result,
                    "count": len(result),
                }

            elif tool_name == "get_related_accounts":
                result = {
                    "account_id": validated_input.account_id,
                    "related_accounts": result,
                    "count": len(result),
                }

            # 8. Output validation
            validated_output = tool.output_schema.model_validate(
                result
            )

            status = "SUCCESS"
            return validated_output.model_dump(mode="json")

        except ToolTimeoutError as exc:
            status = "TIMEOUT"
            error_type = type(exc).__name__
            raise

        except Exception as exc:
            status = "FAILED"
            error_type = type(exc).__name__
            raise

        finally:
            # 9. Record execution telemetry
            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            event = ToolExecutionEvent(
                tool_call_id=tool_call_id,
                investigation_id=context.investigation_id,
                agent_id=context.agent_id,
                tool_name=tool_name,
                status=status,
                attempt_count=attempts,
                duration_ms=round(duration_ms, 2),
                timestamp=utc_timestamp(),
                error_type=error_type,
            )

            self.telemetry.record(event)

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.execute_async(
                    tool_name=tool_name,
                    arguments=arguments,
                    context=context,
                )
            )

        raise RuntimeError(
            "Use execute_async() inside an event loop"
        )
