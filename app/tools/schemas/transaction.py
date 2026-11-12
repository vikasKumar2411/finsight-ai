
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AccountTransactionsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(
        min_length=1,
        pattern=r"^ACC\d{3}$",
        description="Account identifier, e.g. ACC003",
    )


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    source_account: str
    destination_account: str
    amount: float = Field(gt=0)
    currency: str
    timestamp: datetime
    description: str


class AccountTransactionsOutput(BaseModel):
    account_id: str
    transactions: list[Transaction]
    count: int = Field(ge=0)
