import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def get_account_transactions(account_id: str) -> list[dict]:
    """
    Retrieve incoming and outgoing transactions for an account.
    """

    with open(DATA_DIR / "transactions.json") as f:
        transactions = json.load(f)

    return [
        tx for tx in transactions
        if tx["source_account"] == account_id
        or tx["destination_account"] == account_id
    ]