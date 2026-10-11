"""Credential helpers. PINs are never stored or logged in plaintext."""
import hashlib
import hmac
import secrets
from .errors import ValidationError


def validate_pin(pin: str) -> None:
    if not isinstance(pin, str) or len(pin) != 4 or not pin.isdigit():
        raise ValidationError("PIN must contain exactly four digits.")


def hash_secret(secret: str) -> tuple[bytes, bytes]:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return salt, digest


def verify_secret(secret: str, salt: bytes, expected_digest: bytes) -> bool:
    actual = hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(actual, expected_digest)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
