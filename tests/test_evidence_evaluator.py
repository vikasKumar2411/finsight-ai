
from app.agents.evidence_evaluator import evaluate_evidence


def make_state(transactions, findings):
    return {
        "investigation_id": "INV-TEST",
        "alert_id": "ALERT-TEST",
        "account_id": "ACC001",
        "status": "PENDING",
        "transactions": transactions,
        "related_accounts": [],
        "findings": findings,
        "errors": [],
        "assessment": None,
    }


def test_large_transfer_requires_review():
    state = make_state(
        transactions=[
            {
                "transaction_id": "TX001",
                "amount": 45000.0,
                "description": "Wire transfer",
            }
        ],
        findings=[
            {
                "type": "LARGE_TRANSFER",
                "transaction_id": "TX001",
                "amount": 45000.0,
            }
        ],
    )

    result = evaluate_evidence(state)
    assessment = result["assessment"]

    assert assessment["decision"] == "NEEDS_HUMAN_REVIEW"
    assert assessment["risk_level"] == "UNDETERMINED"

    assert len(assessment["supporting_evidence"]) == 1


def test_equipment_purchase_is_contextual_evidence():
    state = make_state(
        transactions=[
            {
                "transaction_id": "TX002",
                "amount": 30000.0,
                "description": "Equipment purchase",
            }
        ],
        findings=[
            {
                "type": "LARGE_TRANSFER",
                "transaction_id": "TX002",
                "amount": 30000.0,
            }
        ],
    )

    assessment = evaluate_evidence(state)["assessment"]

    assert assessment["decision"] == "NEEDS_HUMAN_REVIEW"
    assert assessment["risk_level"] == "UNDETERMINED"

    assert len(assessment["contextual_evidence"]) == 1
    assert len(assessment["supporting_evidence"]) == 0


def test_relationships_do_not_imply_suspicion():
    state = make_state(
        transactions=[],
        findings=[
            {
                "type": "RELATED_ACCOUNT",
                "account_id": "ACC001",
                "related_account_id": "ACC002",
            }
        ],
    )

    assessment = evaluate_evidence(state)["assessment"]

    assert assessment["decision"] == "NO_THRESHOLD_FLAGS"
    assert assessment["risk_level"] == "UNDETERMINED"

    assert len(assessment["relationship_evidence"]) == 1
