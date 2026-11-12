import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def get_related_accounts(account_id: str) -> list[str]:
    """
    Find accounts directly connected to an account
    through incoming or outgoing transactions.
    """

    with open(DATA_DIR / "transactions.json") as f:
        transactions = json.load(f)

    related_accounts = set()

    for tx in transactions:

        if tx["source_account"] == account_id:
            related_accounts.add(tx["destination_account"])

        elif tx["destination_account"] == account_id:
            related_accounts.add(tx["source_account"])

    return sorted(related_accounts)