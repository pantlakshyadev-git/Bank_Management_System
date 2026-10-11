from decimal import Decimal
import pytest
from bank_app.currency import convert, money, positive_money
from bank_app.errors import ValidationError


def test_money_rounds_to_two_decimal_places():
    assert money("12.345") == Decimal("12.35")


def test_negative_or_zero_transaction_amount_rejected():
    with pytest.raises(ValidationError):
        positive_money("0")
    with pytest.raises(ValidationError):
        positive_money("-2")


def test_demo_currency_conversion():
    assert convert(Decimal("83.00"), "INR", "USD") == Decimal("1.00")


def test_unsupported_currency_rejected():
    with pytest.raises(ValidationError):
        convert(Decimal("10"), "ABC", "USD")
