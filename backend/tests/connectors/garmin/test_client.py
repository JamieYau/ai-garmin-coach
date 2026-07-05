from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from garminconnect import (  # type: ignore[import-untyped]
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from app.connectors.garmin.client import (
    GarminAuthenticationError,
    GarminClient,
    GarminClientError,
    GarminConnectionError,
    GarminCredentials,
    GarminRateLimitError,
)


class FakeRawGarminClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.next_error: Exception | None = None
        self.client = FakeTokenStore()

    def login(self, tokenstore: str | None = None) -> tuple[str | None, str | None]:
        self.calls.append(("login", (tokenstore,)))
        self._raise_next_error()
        return ("oauth1", "oauth2")

    def get_full_name(self) -> str | None:
        self.calls.append(("get_full_name", ()))
        self._raise_next_error()
        return "Garmin Athlete"

    def get_user_profile(self) -> dict[str, Any]:
        self.calls.append(("get_user_profile", ()))
        self._raise_next_error()
        return {"profileId": 123, "displayName": "athlete"}

    def get_activities(
        self,
        start: int = 0,
        limit: int = 20,
        activitytype: str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(("get_activities", (start, limit, activitytype)))
        self._raise_next_error()
        return [{"activityId": 1}, {"activityId": 2}]

    def get_activities_by_date(
        self,
        startdate: str,
        enddate: str | None = None,
        activitytype: str | None = None,
        sortorder: str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(("get_activities_by_date", (startdate, enddate, activitytype, sortorder)))
        self._raise_next_error()
        return [{"activityId": 3, "startDate": startdate, "endDate": enddate}]

    def get_user_summary(self, cdate: str) -> dict[str, Any]:
        self.calls.append(("get_user_summary", (cdate,)))
        self._raise_next_error()
        return {"calendarDate": cdate, "totalSteps": 10000}

    def get_sleep_data(self, cdate: str) -> dict[str, Any]:
        self.calls.append(("get_sleep_data", (cdate,)))
        self._raise_next_error()
        return {"dailySleepDTO": {"calendarDate": cdate}}

    def get_heart_rates(self, cdate: str) -> dict[str, Any]:
        self.calls.append(("get_heart_rates", (cdate,)))
        self._raise_next_error()
        return {"calendarDate": cdate, "heartRateValues": []}

    def get_hrv_data(self, cdate: str) -> dict[str, Any] | None:
        self.calls.append(("get_hrv_data", (cdate,)))
        self._raise_next_error()
        return {"calendarDate": cdate, "hrvReadings": []}

    def _raise_next_error(self) -> None:
        if self.next_error is not None:
            error = self.next_error
            self.next_error = None
            raise error


class FakeTokenStore:
    def dumps(self) -> str:
        return "serialized-tokenstore"


def test_credentials_do_not_expose_password_in_repr() -> None:
    credentials = GarminCredentials(username="athlete@example.test", password="super-secret")

    assert "athlete@example.test" in repr(credentials)
    assert "super-secret" not in repr(credentials)


def test_client_constructs_library_client_with_credentials_and_options() -> None:
    raw_client = FakeRawGarminClient()

    def factory(**kwargs: Any) -> FakeRawGarminClient:
        raw_client.kwargs = kwargs
        return raw_client

    GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        is_cn=True,
        prompt_mfa=lambda: "123456",
        client_factory=factory,
        verify_login=False,
    )

    assert raw_client.kwargs["email"] == "athlete@example.test"
    assert raw_client.kwargs["password"] == "super-secret"
    assert raw_client.kwargs["is_cn"] is True
    assert raw_client.kwargs["prompt_mfa"] is not None
    assert raw_client.kwargs["return_on_mfa"] is False
    assert raw_client.kwargs["verify_login"] is False


def test_login_returns_session_tokens() -> None:
    raw_client = FakeRawGarminClient()
    client = GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        client_factory=lambda **_: raw_client,
    )

    result = client.login(tokenstore="/tmp/garmin-tokenstore")

    assert result.oauth1_token == "oauth1"
    assert result.oauth2_token == "oauth2"
    assert result.has_session_tokens is True
    assert raw_client.calls == [("login", ("/tmp/garmin-tokenstore",))]


def test_client_dumps_tokenstore() -> None:
    raw_client = FakeRawGarminClient()
    client = GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        client_factory=lambda **_: raw_client,
    )

    assert client.dump_tokenstore() == "serialized-tokenstore"


def test_client_wraps_profile_and_data_methods() -> None:
    raw_client = FakeRawGarminClient()
    client = GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        client_factory=lambda **_: raw_client,
    )

    assert client.get_full_name() == "Garmin Athlete"
    assert client.get_user_profile()["profileId"] == 123
    assert client.get_activities(start=5, limit=10, activity_type="running") == [
        {"activityId": 1},
        {"activityId": 2},
    ]
    assert client.get_activities_by_date(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 5),
        activity_type="cycling",
    )[0]["startDate"] == "2026-07-01"
    assert client.get_daily_summary(date(2026, 7, 5))["calendarDate"] == "2026-07-05"
    assert client.get_sleep_data(date(2026, 7, 5))["dailySleepDTO"]["calendarDate"] == "2026-07-05"
    assert client.get_heart_rates(date(2026, 7, 5))["calendarDate"] == "2026-07-05"
    assert client.get_hrv_data(date(2026, 7, 5)) == {
        "calendarDate": "2026-07-05",
        "hrvReadings": [],
    }

    assert ("get_activities", (5, 10, "running")) in raw_client.calls
    assert (
        "get_activities_by_date",
        ("2026-07-01", "2026-07-05", "cycling", None),
    ) in raw_client.calls


def test_client_accepts_dict_activity_response_shape() -> None:
    class DictActivityClient(FakeRawGarminClient):
        def get_activities(
            self,
            start: int = 0,
            limit: int = 20,
            activitytype: str | None = None,
        ) -> dict[str, Any]:
            return {"activities": [{"activityId": 99}]}

    client = GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        client_factory=lambda **_: DictActivityClient(),
    )

    assert client.get_activities() == [{"activityId": 99}]


def test_client_rejects_unexpected_activity_response_shape() -> None:
    class InvalidActivityClient(FakeRawGarminClient):
        def get_activities(
            self,
            start: int = 0,
            limit: int = 20,
            activitytype: str | None = None,
        ) -> dict[str, Any]:
            return {"activities": {"activityId": 99}}

    client = GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        client_factory=lambda **_: InvalidActivityClient(),
    )

    with pytest.raises(GarminClientError, match="activities response"):
        client.get_activities()


@pytest.mark.parametrize(
    ("library_error", "wrapper_error"),
    [
        (GarminConnectAuthenticationError("bad credentials"), GarminAuthenticationError),
        (GarminConnectTooManyRequestsError("too many requests"), GarminRateLimitError),
        (GarminConnectConnectionError("network failed"), GarminConnectionError),
    ],
)
def test_client_translates_library_errors(
    library_error: Exception,
    wrapper_error: type[Exception],
) -> None:
    raw_client = FakeRawGarminClient()
    raw_client.next_error = library_error
    client = GarminClient(
        GarminCredentials(username="athlete@example.test", password="super-secret"),
        client_factory=lambda **_: raw_client,
    )

    with pytest.raises(wrapper_error) as exc_info:
        client.login()

    assert "super-secret" not in str(exc_info.value)
