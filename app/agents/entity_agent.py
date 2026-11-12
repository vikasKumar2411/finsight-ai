
from app.orchestration.state import InvestigationState
from app.tools.gateway import ToolGateway
from app.tools.security.authorization import ExecutionContext


def create_entity_agent(gateway: ToolGateway):

    async def entity_agent(
        state: InvestigationState,
    ) -> dict:

        context = ExecutionContext(
            user_id="analyst_001",
            agent_id="entity_agent",
            investigation_id=state["investigation_id"],
            permissions=frozenset({"accounts:read"}),
        )

        result = await gateway.execute_async(
            tool_name="get_related_accounts",
            arguments={
                "account_id": state["account_id"],
            },
            context=context,
        )

        related_accounts = result["related_accounts"]

        findings = [
            {
                "type": "RELATED_ACCOUNT",
                "account_id": state["account_id"],
                "related_account_id": related_id,
                "reason": (
                    "Account has a direct transaction "
                    "relationship with the investigated account"
                ),
            }
            for related_id in related_accounts
        ]

        return {
            "related_accounts": related_accounts,
            "findings": findings,
        }

    return entity_agent
