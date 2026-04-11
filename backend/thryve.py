"""Thryve Health API client for V.I.T.A.L.

Wraps the Thryve REST API (https://api.thryve.de/v5) to fetch
wearable health data for burnout detection.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta

import httpx

from backend.config import (
    DEMO_MODE,
    THRYVE_APP_ID,
    THRYVE_APP_SECRET,
    THRYVE_BASE_URL,
    THRYVE_PASSWORD,
    THRYVE_USER,
)

# Friendly name -> Thryve data source code
METRIC_CODES: dict[str, int] = {
    # Raw biometrics
    "hrv": 3100,
    "resting_hr": 3001,
    "heart_rate": 3000,
    "heart_rate_sleep": 3002,
    "steps": 1000,
    "blood_glucose": 3302,
    "hba1c": 3303,
    # Sleep
    "sleep_duration": 2200,
    "sleep_quality": 2201,
    "sleep_deep": 2202,
    "sleep_rem": 2203,
    "sleep_efficiency": 2200,
    "sleep_regularity": 2220,
    "interdaily_stability": 2221,
    # Thryve analytics (computed by Thryve, not raw)
    "stress": 6010,
    "mental_health_risk": 2254,
    "sick_leave_prediction": 2257,
    "depression_risk": 6406,
    "physical_activity_index": 1013,
    "vo2max": 3030,
    "fitness_age": 3031,
}

# Reverse lookup: code -> friendly name
CODE_NAMES: dict[int, str] = {v: k for k, v in METRIC_CODES.items()}


def _basic_auth(user: str, password: str) -> str:
    """Build a Basic auth header value."""
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


class ThryveClient:
    """Async client for the Thryve Health REST API."""

    def __init__(self) -> None:
        self._base_url = THRYVE_BASE_URL
        self._headers = {
            "Authorization": _basic_auth(THRYVE_USER, THRYVE_PASSWORD),
            "AppAuthorization": _basic_auth(THRYVE_APP_ID, THRYVE_APP_SECRET),
        }

    async def _post(self, endpoint: str, data: dict) -> dict | list:
        """Send a POST request with form-encoded body and return parsed JSON."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}{endpoint}",
                headers=self._headers,
                data=data,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Low-level endpoints
    # ------------------------------------------------------------------

    async def get_daily_values(
        self,
        user_token: str,
        data_sources: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Fetch daily aggregated values. Dates as YYYY-MM-DD."""
        body: dict = {"authenticationToken": user_token}
        if data_sources:
            body["dataSources"] = ",".join(str(c) for c in data_sources)
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        result = await self._post("/dailyDynamicValues", body)
        return result if isinstance(result, list) else result.get("body", [])

    async def get_epoch_values(
        self,
        user_token: str,
        data_sources: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Fetch epoch (time-series) values."""
        body: dict = {"authenticationToken": user_token}
        if data_sources:
            body["dataSources"] = ",".join(str(c) for c in data_sources)
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        result = await self._post("/dynamicEpochValues", body)
        return result if isinstance(result, list) else result.get("body", [])

    async def get_user_info(self, user_token: str) -> dict:
        """Get user profile info."""
        result = await self._post("/userInformation", {"authenticationToken": user_token})
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    async def get_vitals(self, user_token: str, days: int = 7) -> dict:
        """Fetch HRV, resting HR, sleep quality, and HR-during-sleep for N days.

        Returns a dict keyed by metric name, each containing a list of
        daily values with date and value. When DEMO_MODE is on, returns
        synthetic values tuned to the seeded memory baselines instead of
        hitting Thryve QA (the QA profiles are empty on stage).
        """
        if DEMO_MODE:
            from backend.seed_data import build_demo_vitals

            return build_demo_vitals(days=days)

        codes = [
            METRIC_CODES["hrv"],
            METRIC_CODES["resting_hr"],
            METRIC_CODES["sleep_quality"],
            METRIC_CODES["heart_rate_sleep"],
            METRIC_CODES["steps"],
        ]
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        raw = await self.get_daily_values(
            user_token, data_sources=codes, start_date=start, end_date=end,
        )
        return self._group_by_metric(raw)

    async def get_blood_panel(self, user_token: str, days: int = 30) -> dict:
        """Fetch glucose and HbA1c from Thryve.

        Adds simulated ferritin, cortisol, and vitamin D as static demo
        values (these are not available from wearables).
        """
        if DEMO_MODE:
            from backend.seed_data import build_demo_blood_panel

            return build_demo_blood_panel()

        codes = [METRIC_CODES["blood_glucose"], METRIC_CODES["hba1c"]]
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        raw = await self.get_daily_values(
            user_token, data_sources=codes, start_date=start, end_date=end,
        )
        panel = self._group_by_metric(raw)
        # Simulated lab values for demo (not from wearable)
        panel["ferritin"] = [{"value": 85, "unit": "ng/mL", "simulated": True}]
        panel["cortisol"] = [{"value": 14.2, "unit": "ug/dL", "simulated": True}]
        panel["vitamin_d"] = [{"value": 32, "unit": "ng/mL", "simulated": True}]
        return panel

    async def get_burnout_metrics(self, user_token: str, days: int = 7) -> dict:
        """Fetch burnout-relevant signals: Thryve analytics + raw biometrics.

        Fetches both Thryve-computed scores (stress, mental health risk,
        sick leave prediction) and raw biometrics (HRV, sleep, resting HR)
        for context. Returns raw values plus a 7-day baseline average.
        """
        if DEMO_MODE:
            from backend.seed_data import build_demo_burnout_metrics

            return build_demo_burnout_metrics(days=days)

        codes = [
            # Thryve analytics (computed scores)
            METRIC_CODES["stress"],
            METRIC_CODES["mental_health_risk"],
            METRIC_CODES["sick_leave_prediction"],
            # Raw biometrics (for context / fallback)
            METRIC_CODES["hrv"],
            METRIC_CODES["sleep_quality"],
            METRIC_CODES["sleep_regularity"],
            METRIC_CODES["resting_hr"],
        ]
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        raw = await self.get_daily_values(
            user_token, data_sources=codes, start_date=start, end_date=end,
        )
        grouped = self._group_by_metric(raw)

        result: dict = {}
        for name, values in grouped.items():
            numeric = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
            baseline = sum(numeric) / len(numeric) if numeric else None
            result[name] = {
                "values": values,
                "baseline_7d": round(baseline, 2) if baseline is not None else None,
                "latest": numeric[-1] if numeric else None,
                "count": len(numeric),
            }
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _group_by_metric(raw: list[dict]) -> dict[str, list[dict]]:
        """Group raw Thryve response entries by friendly metric name."""
        grouped: dict[str, list[dict]] = {}
        for entry in raw:
            code = entry.get("dataSource") or entry.get("dynamicValueType")
            if code is None:
                continue
            code = int(code)
            name = CODE_NAMES.get(code, str(code))
            grouped.setdefault(name, []).append({
                "date": entry.get("date") or entry.get("createdAt"),
                "value": entry.get("value"),
                "unit": entry.get("unit"),
            })
        return grouped
