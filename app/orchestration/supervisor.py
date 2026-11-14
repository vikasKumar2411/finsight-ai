
from app.orchestration.state import InvestigationState


def create_supervisor(
    max_rounds: int = 2,
):
    """
    Create a deterministic, bounded supervisor.

    A round means one evidence evaluation followed
    by one supervisor decision.
    """

    if max_rounds < 1:
        raise ValueError("max_rounds must be >= 1")

    def supervisor(state: InvestigationState) -> dict:
        rounds = state.get("supervisor_rounds", 0) + 1

        completed = set(
            state.get("completed_capabilities", [])
        )

        findings = state["findings"]

        large_transfer_found = any(
            finding["type"] == "LARGE_TRANSFER"
            for finding in findings
        )

        # Stop when the evaluation limit is reached.
        if rounds >= max_rounds:
            return {
                "supervisor_rounds": rounds,
                "next_agent": None,
            }

        # Explicit demonstration policy:
        # investigate connected accounts if a large
        # transfer was found and entity analysis is missing.
        if (
            large_transfer_found
            and "transaction_analysis" in completed
            and "entity_investigation" not in completed
        ):
            return {
                "supervisor_rounds": rounds,
                "next_agent": "entity_investigation",
            }

        # No additional work is justified by this policy.
        return {
            "supervisor_rounds": rounds,
            "next_agent": None,
        }

    return supervisor
