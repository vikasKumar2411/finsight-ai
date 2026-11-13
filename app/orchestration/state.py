
import operator
from typing import Annotated, Any, TypedDict


class InvestigationState(TypedDict):
    investigation_id: str
    alert_id: str
    account_id: str

    status: str

    transactions: list[dict[str, Any]]
    related_accounts: list[str]

    findings: Annotated[
        list[dict[str, Any]],
        operator.add,
    ]

    errors: Annotated[
        list[str],
        operator.add,
    ]

    assessment: dict[str, Any] | None
