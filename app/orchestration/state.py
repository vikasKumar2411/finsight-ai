
from typing import Any, TypedDict


class InvestigationState(TypedDict):
    investigation_id: str
    alert_id: str
    account_id: str
    status: str
    transactions: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    errors: list[str]
