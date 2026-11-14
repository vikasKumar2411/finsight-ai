
from app.orchestration.state import InvestigationState
from app.tools.gateway import ToolGateway
from app.tools.security.authorization import ExecutionContext


LARGE_TRANSFER_THRESHOLD = 20_000


def create_transaction_agent(
    gateway: ToolGateway,
):
    """
    Factory that creates a LangGraph node
    with access to the Tool Gateway.
    """

    async def transaction_agent(
        state: InvestigationState,
    ) -> dict:

        context = ExecutionContext(
            user_id="analyst_001",
            agent_id="transaction_agent",
            investigation_id=state["investigation_id"],
            permissions=frozenset({"transactions:read"}),
        )

        # 1. Retrieve transactions through the Gateway
        result = await gateway.execute_async(
            tool_name="get_account_transactions",
            arguments={
                "account_id": state["account_id"],
            },
            context=context,
        )

        transactions = result["transactions"]

        # 2. Analyze transactions
        findings = []

        for tx in transactions:
            if tx["amount"] > LARGE_TRANSFER_THRESHOLD:
                findings.append({
                    "type": "LARGE_TRANSFER",
                    "transaction_id": tx["transaction_id"],
                    "amount": tx["amount"],
                    "account_id": state["account_id"],
                    "reason": (
                        "Transaction exceeds the "
                        "synthetic demonstration threshold"
                    ),
                })

        # 3. Return partial state update
        return {
            "transactions": transactions,
            "findings": findings,
            "completed_capabilities": ["transaction_analysis"],
        }

    return transaction_agent
