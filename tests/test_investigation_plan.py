
import pytest

from pydantic import ValidationError

from app.planning.schemas import (
    InvestigationPlan,
    InvestigationCapability,
)


def valid_plan():
    return {
        "investigation_id": "INV-001",
        "alert_id": "ALERT001",
        "investigation_questions": [
            "Which transactions require review?"
        ],
        "steps": [
            {
                "capability": "transaction_analysis",
                "objective": "Analyze transactions for ACC001",
                "rationale": "Transaction evidence is required",
            }
        ],
    }


def test_valid_investigation_plan():
    plan = InvestigationPlan.model_validate(
        valid_plan()
    )

    assert plan.investigation_id == "INV-001"
    assert plan.alert_id == "ALERT001"
    assert len(plan.steps) == 1

    assert plan.steps[0].capability == (
        InvestigationCapability.TRANSACTION_ANALYSIS
    )


def test_invalid_capability_rejected():
    data = valid_plan()

    data["steps"][0]["capability"] = (
        "execute_shell_command"
    )

    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate(data)


def test_duplicate_capabilities_rejected():
    data = valid_plan()

    data["steps"].append({
        "capability": "transaction_analysis",
        "objective": "Analyze account transactions again",
        "rationale": "Repeated investigation step",
    })

    with pytest.raises(
        ValidationError,
        match="Duplicate investigation capabilities",
    ):
        InvestigationPlan.model_validate(data)


def test_excessive_steps_rejected():
    data = valid_plan()

    data["steps"] = [
        {
            "capability": "transaction_analysis",
            "objective": "Analyze account transactions",
            "rationale": "Review financial activity",
        },
        {
            "capability": "entity_investigation",
            "objective": "Analyze account connections",
            "rationale": "Review direct account links",
        },
        {
            "capability": "transaction_analysis",
            "objective": "Repeat transaction analysis",
            "rationale": "Review transactions again",
        },
    ]

    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate(data)


def test_extra_fields_rejected():
    data = valid_plan()

    data["unrestricted_tool_access"] = True

    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate(data)


def test_empty_plan_rejected():
    data = valid_plan()

    data["steps"] = []

    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate(data)


def test_plan_serialization():
    plan = InvestigationPlan.model_validate(
        valid_plan()
    )

    serialized = plan.model_dump(mode="json")

    assert serialized["steps"][0]["capability"] == (
        "transaction_analysis"
    )

    assert serialized["investigation_id"] == "INV-001"
