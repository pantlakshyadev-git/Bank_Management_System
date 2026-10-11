"""Currency utilities. Rates are illustrative demo values, not live market data."""
from decimal import Decimal, ROUND_HALF_UP
from .errors import ValidationError

# Number of units of each currency per 1 USD. DEMO ONLY; configure a trusted provider for production.
DEMO_UNITS_PER_USD = {
    "USD": Decimal("1"),
    "INR": Decimal("83.00"),
    "EUR": Decimal("0.92"),
    "JPY": Decimal("150.00"),
}
CENT = Decimal("0.01")


def money(value) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValidationError("Enter a valid monetary amount.") from exc
    if not amount.is_finite():
        raise ValidationError("Amount must be a finite number.")
    return amount


def positive_money(value) -> Decimal:
    amount = money(value)
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    return amount


def convert(amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
    source, target = from_currency.upper(), to_currency.upper()
    if source not in DEMO_UNITS_PER_USD or target not in DEMO_UNITS_PER_USD:
        raise ValidationError("Unsupported currency. Supported currencies: USD, INR, EUR, JPY.")
    usd = amount / DEMO_UNITS_PER_USD[source]
    return (usd * DEMO_UNITS_PER_USD[target]).quantize(CENT, rounding=ROUND_HALF_UP)
