import base64
import hashlib
import hmac
import json
from secrets import compare_digest
from typing import Any
from urllib.parse import unquote

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request

REDACTED_VALUE = "[redacted]"
SENSITIVE_PAYLOAD_SCHEMA_VERSION = 1
SENSITIVE_PAYLOAD_ALGORITHM = "fernet-sha256"
BETTER_AUTH_SESSION_COOKIE_NAME = "better-auth.session_token"
BETTER_AUTH_SECURE_SESSION_COOKIE_NAME = "__Secure-better-auth.session_token"


def constant_time_equals(left: str, right: str) -> bool:
    return compare_digest(left, right)


def redact_secret(value: str | None) -> str | None:
    if not value:
        return value
    return REDACTED_VALUE


def _fernet_for_secret(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_json_payload(payload: dict[str, Any], secret: str) -> dict[str, str | int]:
    """Encrypt a JSON object for storage in database metadata fields."""
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = _fernet_for_secret(secret).encrypt(plaintext).decode("ascii")
    return {
        "schema_version": SENSITIVE_PAYLOAD_SCHEMA_VERSION,
        "algorithm": SENSITIVE_PAYLOAD_ALGORITHM,
        "ciphertext": ciphertext,
    }


def decrypt_json_payload(envelope: dict[str, Any], secret: str) -> dict[str, Any]:
    if (
        envelope.get("schema_version") != SENSITIVE_PAYLOAD_SCHEMA_VERSION
        or envelope.get("algorithm") != SENSITIVE_PAYLOAD_ALGORITHM
    ):
        raise ValueError("Unsupported encrypted payload envelope")

    ciphertext = envelope.get("ciphertext")
    if not isinstance(ciphertext, str) or not ciphertext:
        raise ValueError("Encrypted payload envelope is missing ciphertext")

    try:
        plaintext = _fernet_for_secret(secret).decrypt(ciphertext.encode("ascii"))
    except InvalidToken as exc:
        raise ValueError("Encrypted payload could not be decrypted") from exc

    decoded = json.loads(plaintext.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Encrypted payload did not contain a JSON object")
    return decoded


def encrypt_sensitive_payload(payload: dict[str, Any], secret: str) -> dict[str, str | int]:
    """Encrypt credentials, tokens, or provider session material before persistence."""
    return encrypt_json_payload(payload, secret)


def decrypt_sensitive_payload(envelope: dict[str, Any], secret: str) -> dict[str, Any]:
    """Decrypt previously persisted credentials, tokens, or provider session material."""
    return decrypt_json_payload(envelope, secret)


def _sign_cookie_value(value: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("ascii")
    return f"{value}.{signature}"


def verify_signed_cookie_value(signed_value: str, secret: str) -> str | None:
    signed_value = unquote(signed_value)
    value, separator, _signature = signed_value.rpartition(".")
    if not separator:
        return None

    expected = _sign_cookie_value(value, secret)
    if not constant_time_equals(signed_value, expected):
        return None

    return value


def get_better_auth_session_token(request: Request, secret: str) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, separator, token = authorization.partition(" ")
        if separator and scheme.lower() == "bearer" and token.strip():
            return token.strip()

    signed_cookie = request.cookies.get(BETTER_AUTH_SESSION_COOKIE_NAME) or request.cookies.get(
        BETTER_AUTH_SECURE_SESSION_COOKIE_NAME
    )
    if not signed_cookie:
        return None

    return verify_signed_cookie_value(signed_cookie, secret)


def create_better_auth_session_cookie_value(token: str, secret: str) -> str:
    return _sign_cookie_value(token, secret)
