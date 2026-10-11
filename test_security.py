import pytest
from bank_app.errors import ValidationError
from bank_app.security import hash_secret, validate_pin, verify_secret


def test_pin_validation():
    validate_pin("0427")
    for pin in ("123", "12345", "12a4", "abcd", ""):
        with pytest.raises(ValidationError):
            validate_pin(pin)


def test_secret_hash_verifies_and_salts_are_unique():
    salt1, digest1 = hash_secret("1234")
    salt2, digest2 = hash_secret("1234")
    assert verify_secret("1234", salt1, digest1)
    assert not verify_secret("9999", salt1, digest1)
    assert salt1 != salt2
    assert digest1 != digest2
