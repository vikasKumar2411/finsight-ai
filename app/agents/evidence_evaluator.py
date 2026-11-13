
from app.orchestration.state import InvestigationState


def evaluate_evidence(
    state: InvestigationState,
) -> dict:
    """
    Evaluate combined findings from the Transaction
    and Entity Agents.

    This deterministic version does not determine
    whether fraud or suspicious activity occurred.
    """

    findings = state["findings"]
    transactions = state["transactions"]

    transaction_lookup = {
        tx["transaction_id"]: tx
        for tx in transactions
    }

    large_transfers = [
        finding
        for finding in findings
        if finding["type"] == "LARGE_TRANSFER"
    ]

    related_accounts = [
        finding
        for finding in findings
        if finding["type"] == "RELATED_ACCOUNT"
    ]

    supporting_evidence = []
    contextual_evidence = []

    # 1. Review large-transfer observations.
    for finding in large_transfers:

        transaction_id = finding["transaction_id"]
        transaction = transaction_lookup.get(
            transaction_id
        )

        if transaction is None:
            continue

        description = (
            transaction.get("description") or ""
        ).lower()

        evidence = {
            "transaction_id": transaction_id,
            "amount": transaction["amount"],
            "description": transaction.get(
                "description", ""
            ),
        }

        # A description mentioning equipment is
        # contextual information, not proof of legitimacy.
        if "equipment" in description:
            contextual_evidence.append({
                **evidence,
                "interpretation": (
                    "Transaction description suggests an "
                    "equipment-related purpose, but this "
                    "has not been independently verified."
                ),
            })

        else:
            supporting_evidence.append({
                **evidence,
                "interpretation": (
                    "Transaction exceeds the synthetic "
                    "large-transfer threshold and warrants "
                    "further contextual review."
                ),
            })

    # 2. Summarize account relationships.
    relationship_evidence = [
        {
            "account_id": f["account_id"],
            "related_account_id": (
                f["related_account_id"]
            ),
            "interpretation": (
                "Direct transaction relationship observed; "
                "no adverse inference established."
            ),
        }
        for f in related_accounts
    ]

    # 3. Determine preliminary review disposition.
    requires_review = bool(large_transfers)

    assessment = {
        "decision": (
            "NEEDS_HUMAN_REVIEW"
            if requires_review
            else "NO_THRESHOLD_FLAGS"
        ),
        "risk_level": "UNDETERMINED",
        "supporting_evidence": supporting_evidence,
        "contextual_evidence": contextual_evidence,
        "relationship_evidence": relationship_evidence,
        "limitations": [
            "Transaction descriptions are unverified.",
            "No customer baseline or historical behavior "
            "has been evaluated.",
            "Account relationships alone do not establish "
            "suspicious activity.",
            "No determination of fraud or regulatory "
            "suspicion has been made.",
        ],
        "summary": (
            "Large-transfer observations require further "
            "contextual investigation."
            if requires_review
            else "No large-transfer threshold flags were "
            "identified in the retrieved transactions."
        ),
    }

    return {
        "assessment": assessment,
    }
