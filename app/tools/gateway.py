
# app/tools/gateway.py

import asyncio
import inspect
from typing import Any

from app.tools.registry import ToolRegistry

from app.tools.execution.retry import (
    TransientToolError,
    execute_with_retry,
)
from app.tools.execution.timeout import (
    execute_with_timeout,
)
from app.tools.security.authorization import (
    ExecutionContext,
    ToolAuthorizer,
)


class ToolGateway:

    def __init__(
        self,
        registry: ToolRegistry,
        authorizer: ToolAuthorizer,
    ):
        self.registry = registry
        self.authorizer = authorizer

    async def execute_async(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:

        # 1. Resolve registered tool
        tool = self.registry.get(tool_name)

        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        # 2. Validate input
        validated_input = tool.input_schema.model_validate(
            arguments
        )

        # 3. Authorize before any execution
        self.authorizer.authorize(
            required_permission=tool.required_permission,
            context=context,
        )

        # 4. Define a single execution attempt
        async def execute_attempt():
            return await execute_with_timeout(
                handler=tool.handler,
                arguments=validated_input.model_dump(),
                timeout_seconds=tool.timeout_seconds,
            )

        # 5. Apply tool-specific retry policy
        result = await execute_with_retry(
            operation=execute_attempt,
            max_attempts=tool.max_attempts,
            retryable_exceptions=(TransientToolError,),
        )

        # 6. Adapt existing tool outputs
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

        # 7. Validate output
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
        """
        Synchronous convenience interface.

        Use execute_async() when already inside
        an async application or event loop.
        """

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
