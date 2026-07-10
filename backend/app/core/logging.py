from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.security import REDACTED_VALUE

SENSITIVE_FIELD_NAMES = {
    "access_token",
    "api_key",
    "authorization",
    "bearer",
    "ciphertext",
    "cookie",
    "credentials",
    "garmin_password",
    "mfa",
    "mfa_code",
    "openai_api_key",
    "password",
    "prompt",
    "raw_payload",
    "refresh_token",
    "secret",
    "session",
    "session_material",
    "token",
    "tokenstore",
}

LOG_RECORD_BUILTINS = set(logging.makeLogRecord({}).__dict__)


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_field(key_text):
                redacted[key_text] = REDACTED_VALUE
            else:
                redacted[key_text] = redact_sensitive_data(item)
        return redacted

    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)

    if isinstance(value, list | set):
        return [redact_sensitive_data(item) for item in value]

    return value


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, dict):
            record.msg = redact_sensitive_data(record.msg)
        if record.args:
            record.args = redact_sensitive_data(record.args)
        for key, value in list(record.__dict__.items()):
            if key in LOG_RECORD_BUILTINS:
                continue
            record.__dict__[key] = (
                REDACTED_VALUE if _is_sensitive_field(key) else redact_sensitive_data(value)
            )
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in LOG_RECORD_BUILTINS and not key.startswith("_")
        }
        if extras:
            log_entry["extra"] = redact_sensitive_data(extras)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(redact_sensitive_data(log_entry), sort_keys=True, default=str)


def configure_logging(level: str) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(_logging_level(level))

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(handler)


def _is_sensitive_field(field_name: str) -> bool:
    normalized = field_name.lower().replace("-", "_")
    return any(name in normalized for name in SENSITIVE_FIELD_NAMES)


def _logging_level(level: str) -> int:
    return getattr(logging, level.strip().upper(), logging.INFO)
