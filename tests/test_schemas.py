
import pytest
from pydantic import ValidationError

from app.tools.schemas.transaction import AccountTransactionsInput
from app.tools.schemas.entity import RelatedAccountsInput


def test_valid_transaction_input():
    data = AccountTransactionsInput(account_id="ACC003")
    assert data.account_id == "ACC003"


def test_invalid_transaction_input():
    with pytest.raises(ValidationError):
        AccountTransactionsInput(account_id="INVALID")


def test_missing_transaction_input():
    with pytest.raises(ValidationError):
        AccountTransactionsInput()


def test_valid_entity_input():
    data = RelatedAccountsInput(account_id="ACC004")
    assert data.account_id == "ACC004"


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        AccountTransactionsInput(
            account_id="ACC003",
            admin_override=True,
        )
