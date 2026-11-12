
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
rng = random.Random(SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
EVAL_DIR = ROOT / "data" / "evaluation"

RAW_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

BASE_DATE = datetime(2026, 11, 1, tzinfo=timezone.utc)


def timestamp(days=0, minutes=0):
    return (
        BASE_DATE + timedelta(days=days, minutes=minutes)
    ).isoformat()


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))


# 1. Generate customers
customers = []

for i in range(1, 26):
    customers.append({
        "customer_id": f"C{i:03d}",
        "name": f"Synthetic Customer {i}",
        "customer_type": "Business" if i % 3 == 0 else "Individual",
        "country": "US",
        "risk_rating": rng.choice(["LOW", "MEDIUM"]),
    })


# 2. Generate accounts
accounts = []
countries = ["US", "GB", "DE", "SG", "CA"]

for i in range(1, 41):
    customer = customers[(i - 1) % len(customers)]

    accounts.append({
        "account_id": f"ACC{i:03d}",
        "customer_id": customer["customer_id"],
        "account_type": "CHECKING",
        "country": countries[(i - 1) % len(countries)],
        "status": "ACTIVE",
    })


# 3. Transaction generator
transactions = []


def add_transaction(source, destination, amount, days, minutes=0,
                    description="Synthetic transfer"):
    transaction_id = f"TX{len(transactions) + 1:05d}"

    transaction = {
        "transaction_id": transaction_id,
        "source_account": source,
        "destination_account": destination,
        "amount": round(amount, 2),
        "currency": "USD",
        "timestamp": timestamp(days, minutes),
        "description": description,
    }

    transactions.append(transaction)
    return transaction_id


# Generate 488 background transactions.
# Reserve accounts 1-13 for controlled investigation scenarios.
background_accounts = [
    account["account_id"] for account in accounts[13:]
]

for _ in range(488):
    source, destination = rng.sample(background_accounts, 2)

    add_transaction(
        source=source,
        destination=destination,
        amount=rng.uniform(20, 5000),
        days=rng.randint(-60, -1),
        minutes=rng.randint(0, 1439),
    )


# 4. Plant five investigation scenarios

# Scenario 1: Unusually large transfer
large_tx = add_transaction(
    "ACC001", "ACC002", 45000, 1,
    description="Large outgoing transfer"
)

# Scenario 2: Rapid movement through multiple accounts
rapid_ids = [
    add_transaction("ACC003", "ACC004", 19000, 2, 0),
    add_transaction("ACC004", "ACC005", 18500, 2, 5),
    add_transaction("ACC005", "ACC006", 18000, 2, 10),
    add_transaction("ACC006", "ACC007", 17500, 2, 15),
]

# Scenario 3: Circular fund movement
circular_ids = [
    add_transaction("ACC008", "ACC009", 12000, 3, 0),
    add_transaction("ACC009", "ACC010", 11800, 3, 20),
    add_transaction("ACC010", "ACC008", 11500, 3, 40),
]

# Scenario 4: Cross-border transfers
cross_border_ids = [
    add_transaction("ACC011", "ACC012", 22000, 4, 0),
    add_transaction("ACC012", "ACC013", 21500, 4, 30),
    add_transaction("ACC013", "ACC011", 21000, 4, 60),
]

# Scenario 5: Large transfer with a documented business explanation
benign_tx = add_transaction(
    "ACC001", "ACC003", 30000, 5,
    description="Documented equipment purchase, invoice INV-5001"
)

assert len(transactions) == 500


# 5. Generate investigation alerts
scenarios = [
    ("LARGE_TRANSFER", "ACC001", [large_tx]),
    ("RAPID_FUND_MOVEMENT", "ACC003", rapid_ids),
    ("CIRCULAR_TRANSFERS", "ACC008", circular_ids),
    ("CROSS_BORDER_ACTIVITY", "ACC011", cross_border_ids),
    ("UNUSUAL_TRANSFER", "ACC001", [benign_tx]),
]

alerts = []
expected_findings = []

for i, (alert_type, account_id, transaction_ids) in enumerate(
    scenarios, start=1
):
    alert_id = f"ALERT{i:03d}"

    alerts.append({
        "alert_id": alert_id,
        "alert_type": alert_type,
        "account_id": account_id,
        "trigger_transaction_ids": transaction_ids,
        "status": "OPEN",
    })

    expected_findings.append({
        "alert_id": alert_id,
        "scenario": alert_type,
        "expected_transaction_ids": transaction_ids,
        "expected_outcome": (
            "BENIGN_EXPLANATION_TO_VERIFY"
            if i == 5 else "REQUIRES_INVESTIGATION"
        ),
    })


# 6. Persist generated datasets
save_json(RAW_DIR / "customers.json", customers)
save_json(RAW_DIR / "accounts.json", accounts)
save_json(RAW_DIR / "transactions.json", transactions)
save_json(RAW_DIR / "alerts.json", alerts)
save_json(EVAL_DIR / "expected_findings.json", expected_findings)

print("FinSight AI synthetic data generated successfully.")
print(f"Customers: {len(customers)}")
print(f"Accounts: {len(accounts)}")
print(f"Transactions: {len(transactions)}")
print(f"Alerts: {len(alerts)}")
print(f"Expected findings: {len(expected_findings)}")
