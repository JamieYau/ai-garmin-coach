from secrets import compare_digest

REDACTED_VALUE = "[redacted]"


def constant_time_equals(left: str, right: str) -> bool:
    return compare_digest(left, right)


def redact_secret(value: str | None) -> str | None:
    if not value:
        return value
    return REDACTED_VALUE
