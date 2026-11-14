
# scripts/test_resume.py

import argparse
import asyncio
import os
from uuid import uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.orchestration.graph import build_investigation_graph
from app.tools.registry import create_tool_registry
from app.tools.gateway import ToolGateway
from app.tools.security.authorization import ToolAuthorizer
from app.tools.execution.budget import ExecutionBudgetManager
from app.tools.telemetry import ToolTelemetry


def create_gateway(investigation_id: str) -> ToolGateway:
    # Phase 7.2 still uses an in-memory tool budget.
    # Durable budgets will be implemented separately.
    budget = ExecutionBudgetManager()

    budget.create_budget(
        investigation_id=investigation_id,
        max_tool_calls=20,
    )

    return ToolGateway(
        registry=create_tool_registry(),
        authorizer=ToolAuthorizer(),
        budget_manager=budget,
        telemetry=ToolTelemetry(),
    )


def initial_state(investigation_id: str) -> dict:
    return {
        "investigation_id": investigation_id,
        "alert_id": "ALERT001",
        "account_id": "ACC001",
        "status": "PENDING",
        "transactions": [],
        "related_accounts": [],
        "findings": [],
        "errors": [],
        "assessment": None,
        "completed_capabilities": [],
        "supervisor_rounds": 0,
        "next_agent": None,
    }


def thread_config(investigation_id: str) -> dict:
    return {
        "configurable": {
            "thread_id": investigation_id,
        }
    }


def database_url() -> str:
    url = os.getenv("FINSIGHT_DATABASE_URL")

    if not url:
        raise RuntimeError(
            "Set FINSIGHT_DATABASE_URL before running."
        )

    return url


async def start_investigation() -> None:
    investigation_id = f"INV-RESUME-{uuid4().hex[:8]}"
    config = thread_config(investigation_id)

    async with AsyncPostgresSaver.from_conn_string(
        database_url()
    ) as checkpointer:

        await checkpointer.setup()

        gateway = create_gateway(investigation_id)

        graph = build_investigation_graph(
            gateway=gateway,
            checkpointer=checkpointer,
        )

        # Execute all initial agents and evaluate evidence.
        # Pause BEFORE the supervisor executes.
        await graph.ainvoke(
            initial_state(investigation_id),
            config=config,
            interrupt_before=["supervisor"],
        )

        snapshot = await graph.aget_state(config)

        assert snapshot.next == ("supervisor",), (
            f"Unexpected pending nodes: {snapshot.next}"
        )

        state = snapshot.values

        assert set(state["completed_capabilities"]) == {
            "transaction_analysis",
            "entity_investigation",
        }

        print("\n=== INVESTIGATION PAUSED ===")
        print("Investigation ID:", investigation_id)
        print("Status:", state["status"])
        print("Findings:", len(state["findings"]))
        print(
            "Completed capabilities:",
            state["completed_capabilities"],
        )
        print("Next nodes:", snapshot.next)

        print("\nCheckpoint persisted to PostgreSQL.")
        print("This Python process can now exit.")

        print("\nRESUME WITH:")
        print(
            f"python -m scripts.test_resume resume "
            f"{investigation_id}"
        )


async def resume_investigation(
    investigation_id: str,
) -> None:
    config = thread_config(investigation_id)

    # A new invocation opens a new database connection.
    # The caller can be an entirely new Python process.
    async with AsyncPostgresSaver.from_conn_string(
        database_url()
    ) as checkpointer:

        gateway = create_gateway(investigation_id)

        graph = build_investigation_graph(
            gateway=gateway,
            checkpointer=checkpointer,
        )

        snapshot_before = await graph.aget_state(config)

        if not snapshot_before.values:
            raise ValueError(
                f"No checkpoint found for {investigation_id}"
            )

        if snapshot_before.next != ("supervisor",):
            raise ValueError(
                "Investigation is not paused before supervisor. "
                f"Pending nodes: {snapshot_before.next}"
            )

        saved_state = snapshot_before.values

        assert saved_state["investigation_id"] == (
            investigation_id
        )

        completed_before = list(
            saved_state["completed_capabilities"]
        )
        findings_before = list(saved_state["findings"])
        transactions_before = list(
            saved_state["transactions"]
        )
        related_accounts_before = list(
            saved_state["related_accounts"]
        )

        print("\n=== RECOVERED PAUSED INVESTIGATION ===")
        print("Investigation:", investigation_id)
        print("Findings before resume:", len(findings_before))
        print("Next nodes:", snapshot_before.next)

        # IMPORTANT:
        # None means continue existing execution.
        # Passing initial_state() here would start new work.
        final_state = await graph.ainvoke(
            None,
            config=config,
        )

        snapshot_after = await graph.aget_state(config)

        # Previously completed agent results should
        # remain unchanged. No new agent is needed
        # in this deterministic demonstration.
        assert final_state["completed_capabilities"] == (
            completed_before
        )
        assert final_state["findings"] == findings_before
        assert final_state["transactions"] == (
            transactions_before
        )
        assert final_state["related_accounts"] == (
            related_accounts_before
        )

        assert final_state["status"] == (
            "EVIDENCE_EVALUATION_COMPLETED"
        )
        assert final_state["supervisor_rounds"] == 1
        assert snapshot_after.next == ()

        print("\n=== INVESTIGATION RESUMED ===")
        print("Investigation:", investigation_id)
        print("Final status:", final_state["status"])
        print("Final findings:", len(final_state["findings"]))
        print(
            "Completed capabilities:",
            final_state["completed_capabilities"],
        )
        print(
            "Supervisor rounds:",
            final_state["supervisor_rounds"],
        )
        print("Pending nodes:", snapshot_after.next)

        print("\nDurable investigation resumption verified.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FinSight AI durable resume demonstration"
    )

    parser.add_argument(
        "action",
        choices=["start", "resume"],
    )

    parser.add_argument(
        "investigation_id",
        nargs="?",
    )

    args = parser.parse_args()

    if args.action == "start":
        if args.investigation_id:
            parser.error(
                "Do not supply an investigation ID with start."
            )
        asyncio.run(start_investigation())

    elif args.action == "resume":
        if not args.investigation_id:
            parser.error(
                "resume requires an investigation ID."
            )
        asyncio.run(
            resume_investigation(args.investigation_id)
        )


if __name__ == "__main__":
    main()
