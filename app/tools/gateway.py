from typing import Any

from app.tools.registry import ToolRegistry
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

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:

        # 1. Resolve registered tool
        tool = self.registry.get(tool_name)

        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        # 2. Validate input arguments
        validated_input = tool.input_schema.model_validate(arguments)

        # 3. Authorize execution
        self.authorizer.authorize(
            required_permission=tool.required_permission,
            context=context,
        )

        # 4. Execute registered handler
        result = tool.handler(**validated_input.model_dump())

        # 5. Adapt existing tool outputs
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

        # 6. Validate output
        validated_output = tool.output_schema.model_validate(result)

        return validated_output.model_dump(mode="json")