
import asyncio
import json
from pathlib import Path

from app.orchestration.graph import build_investigation_graph

from app.tools.registry import create_tool_registry
from app.tools.gateway import ToolGateway
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.telemetry import ToolTelemetry
from app.planning.planner import InvestigationPlanner

ROOT = Path(__file__).resolve().parents[1]


async def main():

    # 1. Load synthetic investigation alert
    alerts_path = ROOT / "data" / "raw" / "alerts.json"

    with open(alerts_path) as f:
        alerts = json.load(f)

    alert = next(
        alert for alert in alerts
        if alert["alert_id"] == "ALERT001"
    )

    investigation_id = "INV-001"

    # 2. Initialize shared execution budget
    budget_manager = ExecutionBudgetManager()
    budget_manager.create_budget(
        investigation_id=investigation_id,
        max_tool_calls=20,
    )

    # 3. Initialize the Tool Layer
    telemetry = ToolTelemetry()

    gateway = ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget_manager,
        telemetry=telemetry,
    )

    # 4. Build LangGraph
    # Generate an investigation plan using local Ollama
    planner = InvestigationPlanner()

    alert_description = alert.get(
        "description",
        f"Investigate financial alert {alert['alert_id']} "
        f"for account {alert['account_id']}.",
    )

    plan = await planner.create_plan(
        investigation_id=investigation_id,
        alert_id=alert["alert_id"],
        alert_description=alert_description,
    )

    print("\n=== LLM INVESTIGATION PLAN ===")
    print(json.dumps(plan.model_dump(mode="json"), indent=2))

    # Construct LangGraph using the selected capabilities
    graph = build_investigation_graph(
        gateway=gateway,
        plan=plan,
    )

    # 5. Construct initial investigation state
    initial_state = {
        "investigation_id": investigation_id,
        "alert_id": alert["alert_id"],
        "account_id": alert["account_id"],
        "status": "PENDING",
        "related_accounts": [],
        "assessment": None,
        "transactions": [],
        "findings": [],
        "errors": [],
    }

    # 6. Execute investigation
    final_state = await graph.ainvoke(initial_state)

    # 7. Inspect results
    print("\n=== FIN SIGHT INVESTIGATION ===")
    print("Investigation:", final_state["investigation_id"])
    print("Alert:", final_state["alert_id"])
    print("Status:", final_state["status"])

    print("\nFindings:")
    print(json.dumps(final_state["findings"], indent=2))

    print("\nRelated Accounts:")
    print(json.dumps(final_state["related_accounts"], indent=2))

    print("\nPreliminary Assessment:")
    print(json.dumps(final_state["assessment"], indent=2))

    print("\nExecution Budget:")
    print(budget_manager.get_budget(investigation_id))

    print("\nTool Telemetry:")
    for event in telemetry.get_events():
        print(event)


if __name__ == "__main__":
    asyncio.run(main())
