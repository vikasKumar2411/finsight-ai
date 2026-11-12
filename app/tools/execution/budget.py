
from dataclasses import dataclass
from threading import Lock


class BudgetExceededError(Exception):
    """Investigation has exhausted its tool-call budget."""


class BudgetNotFoundError(Exception):
    """Investigation has no configured budget."""


@dataclass
class InvestigationBudget:
    investigation_id: str
    max_tool_calls: int
    tool_calls_used: int = 0

    @property
    def remaining(self) -> int:
        return self.max_tool_calls - self.tool_calls_used


class ExecutionBudgetManager:
    """
    In-memory budget management for a single process.

    A lock protects concurrent budget reservations.
    """

    def __init__(self):
        self._budgets: dict[str, InvestigationBudget] = {}
        self._lock = Lock()

    def create_budget(
        self,
        investigation_id: str,
        max_tool_calls: int = 20,
    ) -> None:

        if not investigation_id:
            raise ValueError("investigation_id is required")

        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")

        with self._lock:
            if investigation_id in self._budgets:
                raise ValueError(
                    f"Budget already exists: {investigation_id}"
                )

            self._budgets[investigation_id] = InvestigationBudget(
                investigation_id=investigation_id,
                max_tool_calls=max_tool_calls,
            )

    def reserve_call(self, investigation_id: str) -> int:
        """
        Atomically reserve one tool invocation.

        Returns remaining calls after reservation.
        """

        with self._lock:
            budget = self._budgets.get(investigation_id)

            if budget is None:
                raise BudgetNotFoundError(
                    f"No budget for investigation: {investigation_id}"
                )

            if budget.remaining <= 0:
                raise BudgetExceededError(
                    f"Tool-call budget exhausted: {investigation_id}"
                )

            budget.tool_calls_used += 1

            return budget.remaining

    def get_budget(
        self,
        investigation_id: str,
    ) -> InvestigationBudget:

        with self._lock:
            budget = self._budgets.get(investigation_id)

            if budget is None:
                raise BudgetNotFoundError(
                    f"No budget for investigation: {investigation_id}"
                )

            # Return a snapshot, not the mutable internal object.
            return InvestigationBudget(
                investigation_id=budget.investigation_id,
                max_tool_calls=budget.max_tool_calls,
                tool_calls_used=budget.tool_calls_used,
            )
