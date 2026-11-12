
from pydantic import BaseModel, ConfigDict, Field


class RelatedAccountsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(
        min_length=1,
        pattern=r"^ACC\d{3}$",
        description="Account identifier, e.g. ACC004",
    )


class RelatedAccountsOutput(BaseModel):
    account_id: str
    related_accounts: list[str]
    count: int = Field(ge=0)
