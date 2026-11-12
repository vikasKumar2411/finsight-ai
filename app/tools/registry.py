from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from app.tools.implementations.transaction_tool import (
    get_account_transactions,
)
from app.tools.implementations.entity_tool import (
    get_related_accounts,
)
from app.tools.schemas.transaction import (
    AccountTransactionsInput,
    AccountTransactionsOutput,
)
from app.tools.schemas.entity import (
    RelatedAccountsInput,
    RelatedAccountsOutput,
)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_permission: str
    timeout_seconds: float
    max_attempts: int


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())


def create_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="get_account_transactions",
            description="Retrieve transactions for an account.",
            handler=get_account_transactions,
            input_schema=AccountTransactionsInput,
            output_schema=AccountTransactionsOutput,
            required_permission="transactions:read",
            timeout_seconds=5.0,
            max_attempts=3,
        )
    )

    registry.register(
        ToolDefinition(
            name="get_related_accounts",
            description="Find accounts directly connected by transactions.",
            handler=get_related_accounts,
            input_schema=RelatedAccountsInput,
            output_schema=RelatedAccountsOutput,
            required_permission="accounts:read",
            timeout_seconds=5.0,
            max_attempts=3,
        )
    )

    return registry