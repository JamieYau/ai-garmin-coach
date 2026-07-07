from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol, TypeVar, cast

from garminconnect import (  # type: ignore[import-untyped]
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


class GarminRawClient(Protocol):
    """Subset of the garminconnect client used by this application."""

    client: GarminTokenStore

    def login(self, tokenstore: str | None = None) -> tuple[str | None, str | None]: ...

    def get_full_name(self) -> str | None: ...

    def get_user_profile(self) -> dict[str, Any]: ...

    def get_activities(
        self,
        start: int = 0,
        limit: int = 20,
        activitytype: str | None = None,
    ) -> dict[str, Any] | list[Any]: ...

    def get_activities_by_date(
        self,
        startdate: str,
        enddate: str | None = None,
        activitytype: str | None = None,
        sortorder: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_user_summary(self, cdate: str) -> dict[str, Any]: ...

    def get_sleep_data(self, cdate: str) -> dict[str, Any]: ...

    def get_heart_rates(self, cdate: str) -> dict[str, Any]: ...

    def get_hrv_data(self, cdate: str) -> dict[str, Any] | None: ...


GarminClientFactory = Callable[..., GarminRawClient]
T = TypeVar("T")


class GarminTokenStore(Protocol):
    def dumps(self) -> str: ...


@dataclass(frozen=True)
class GarminCredentials:
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class GarminLoginResult:
    oauth1_token: str | None
    oauth2_token: str | None

    @property
    def has_session_tokens(self) -> bool:
        return self.oauth1_token is not None or self.oauth2_token is not None


class GarminClientError(RuntimeError):
    error_code = "garmin_client_error"


class GarminAuthenticationError(GarminClientError):
    error_code = "garmin_authentication_failed"


class GarminConnectionError(GarminClientError):
    error_code = "garmin_connection_failed"


class GarminRateLimitError(GarminClientError):
    error_code = "garmin_rate_limited"


class GarminMfaRequiredError(GarminClientError):
    error_code = "garmin_mfa_required"


class GarminClient:
    """Narrow wrapper around the third-party Garmin Connect library."""

    def __init__(
        self,
        credentials: GarminCredentials,
        *,
        is_cn: bool = False,
        prompt_mfa: Callable[[], str] | None = None,
        client_factory: GarminClientFactory = Garmin,
        verify_login: bool = True,
    ) -> None:
        self._client = client_factory(
            email=credentials.username,
            password=credentials.password,
            is_cn=is_cn,
            prompt_mfa=prompt_mfa,
            return_on_mfa=False,
            verify_login=verify_login,
        )

    def login(self, *, tokenstore: str | None = None) -> GarminLoginResult:
        oauth1_token, oauth2_token = self._call(self._client.login, tokenstore)
        return GarminLoginResult(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

    def dump_tokenstore(self) -> str:
        return self._call(self._client.client.dumps)

    def get_full_name(self) -> str | None:
        return self._call(self._client.get_full_name)

    def get_user_profile(self) -> dict[str, Any]:
        return self._call(self._client.get_user_profile)

    def get_activities(
        self,
        *,
        start: int = 0,
        limit: int = 20,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        response = self._call(self._client.get_activities, start, limit, activity_type)
        return self._coerce_activity_list(response)

    def get_activities_by_date(
        self,
        *,
        start_date: date,
        end_date: date | None = None,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._call(
            self._client.get_activities_by_date,
            self._format_date(start_date),
            self._format_date(end_date) if end_date is not None else None,
            activity_type,
        )

    def get_daily_summary(self, day: date) -> dict[str, Any]:
        return self._call(self._client.get_user_summary, self._format_date(day))

    def get_sleep_data(self, day: date) -> dict[str, Any]:
        return self._call(self._client.get_sleep_data, self._format_date(day))

    def get_heart_rates(self, day: date) -> dict[str, Any]:
        return self._call(self._client.get_heart_rates, self._format_date(day))

    def get_hrv_data(self, day: date) -> dict[str, Any] | None:
        return self._call(self._client.get_hrv_data, self._format_date(day))

    def _call(self, method: Callable[..., T], *args: object) -> T:
        try:
            return method(*args)
        except GarminConnectAuthenticationError as exc:
            raise GarminAuthenticationError("Garmin authentication failed.") from exc
        except GarminConnectTooManyRequestsError as exc:
            raise GarminRateLimitError("Garmin rate limit exceeded.") from exc
        except GarminConnectConnectionError as exc:
            raise GarminConnectionError("Garmin connection failed.") from exc

    def _coerce_activity_list(self, response: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        if isinstance(response, list):
            return [cast("dict[str, Any]", activity) for activity in response]

        activities = response.get("activities", [])
        if not isinstance(activities, list):
            raise GarminClientError("Garmin activities response did not contain a list.")
        return [cast("dict[str, Any]", activity) for activity in activities]

    def _format_date(self, value: date) -> str:
        return value.isoformat()
