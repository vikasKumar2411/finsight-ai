
from langgraph.graph import StateGraph, START, END

from app.orchestration.state import InvestigationState
from app.agents.transaction_agent import (
    create_transaction_agent,
)
from app.tools.gateway import ToolGateway


def build_investigation_graph(gateway: ToolGateway):
    builder = StateGraph(InvestigationState)

    # Register our first agent node
    builder.add_node(
        "transaction_analysis",
        create_transaction_agent(gateway),
    )

    # Define execution order
    builder.add_edge(START, "transaction_analysis")
    builder.add_edge("transaction_analysis", END)

    return builder.compile()
