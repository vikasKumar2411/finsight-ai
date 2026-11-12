from dataclasses import dataclass


class AuthorizationError(Exception):
    pass


@dataclass(frozen=True)
class ExecutionContext:
    user_id: str
    agent_id: str
    investigation_id: str
    permissions: frozenset[str]


class ToolAuthorizer:

    def authorize(
        self,
        required_permission: str,
        context: ExecutionContext,
    ) -> None:
        if required_permission not in context.permissions:
            raise AuthorizationError(
                f"Permission denied: {required_permission}"
            )