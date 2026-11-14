
# tests/test_resume.py

import asyncio

from langgraph.checkpoint.memory import InMemorySaver

from app.orchestration.graph import build_investigation_graph
from app.tools.gateway import ToolGateway
from app.tools.registry import create_tool_registry
from app.tools.security.authorization import ToolAuthorizer


def test_paused_investigation_resumes_without_rerunning_agents():
    async def run():
        gateway = ToolGateway(
            registry=create_tool_registry(),
            authorizer=ToolAuthorizer(),
        )

        graph = build_investigation_graph(
            gateway=gateway,
            checkpointer=InMemorySaver(),
        )

        config = {
            "configurable": {
                "thread_id": "INV-RESUME-UNIT-TEST",
            }
        }

        initial_state = {
            "investigation_id": "INV-RESUME-UNIT-TEST",
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

        await graph.ainvoke(
            initial_state,
            config=config,
            interrupt_before=["supervisor"],
        )

        paused = await graph.aget_state(config)

        assert paused.next == ("supervisor",)
        assert paused.values["supervisor_rounds"] == 0

        saved_findings = list(paused.values["findings"])
        saved_capabilities = list(
            paused.values["completed_capabilities"]
        )

        resumed = await graph.ainvoke(
            None,
            config=config,
        )

        finished = await graph.aget_state(config)

        assert resumed["findings"] == saved_findings
        assert resumed["completed_capabilities"] == (
            saved_capabilities
        )
        assert resumed["supervisor_rounds"] == 1
        assert resumed["status"] == (
            "EVIDENCE_EVALUATION_COMPLETED"
        )
        assert finished.next == ()

    asyncio.run(run())
