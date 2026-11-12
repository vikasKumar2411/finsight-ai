from app.tools.implementations.transaction_tool import (
    get_account_transactions,
)
from app.tools.implementations.entity_tool import (
    get_related_accounts,
)


def test_account_transactions():
    transactions = get_account_transactions("ACC003")

    assert len(transactions) > 0

    assert all(
        tx["source_account"] == "ACC003"
        or tx["destination_account"] == "ACC003"
        for tx in transactions
    )


def test_related_accounts():
    related = get_related_accounts("ACC004")

    assert "ACC003" in related
    assert "ACC005" in related


def test_unknown_account():
    transactions = get_account_transactions("UNKNOWN")
    related = get_related_accounts("UNKNOWN")

    assert transactions == []
    assert related == []