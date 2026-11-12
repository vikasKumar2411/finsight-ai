
import asyncio
from typing import Any

from app.tools.registry import ToolRegistry
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.execution.retry import (
    TransientToolError,
    execute_with_retry,
)
from app.tools.execution.timeout import execute_with_timeout
from app.tools.security.authorization import (
    ExecutionContext,
    ToolAuthorizer,
)


class ToolGateway:

    def __init__(
        self,
        registry: ToolRegistry,
        authorizer: ToolAuthorizer,
        budget_manager: ExecutionBudgetManager | None = None,
    ):
        self.registry = registry
        self.authorizer = authorizer
        self.budget_manager = budget_manager

    async def execute_async(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:

        # 1. Resolve tool definition
        tool = self.registry.get(tool_name)

        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        # 2. Validate input arguments
        validated_input = tool.input_schema.model_validate(
            arguments
        )

        # 3. Authorize tool invocation
        self.authorizer.authorize(
            required_permission=tool.required_permission,
            context=context,
        )

        # 4. Reserve investigation-level budget
        if self.budget_manager is not None:
            self.budget_manager.reserve_call(
                investigation_id=context.investigation_id
            )

        # 5. Define one tool execution attempt
        async def execute_attempt():
            return await execute_with_timeout(
                handler=tool.handler,
                arguments=validated_input.model_dump(),
                timeout_seconds=tool.timeout_seconds,
            )

        # 6. Execute with bounded retries
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

        # 8. Validate output schema
        validated_output = tool.output_schema.model_validate(
            result
        )

        return validated_output.model_dump(mode="json")

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
