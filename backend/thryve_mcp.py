"""Thryve Health API — MCP Server for Claude Code.

Exposes the full Thryve API as MCP tools so Claude can query
real patient data during development.
"""

import base64
import os
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# --- Config ---
BASE_URL = "https://api.thryve.de/v5"

THRYVE_USER = os.environ.get("THRYVE_USER", "")
THRYVE_PASSWORD = os.environ.get("THRYVE_PASSWORD", "")
THRYVE_APP_ID = os.environ.get("THRYVE_APP_ID", "")
THRYVE_APP_SECRET = os.environ.get("THRYVE_APP_SECRET", "")

AUTH = base64.b64encode(f"{THRYVE_USER}:{THRYVE_PASSWORD}".encode()).decode()
APP_AUTH = base64.b64encode(f"{THRYVE_APP_ID}:{THRYVE_APP_SECRET}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {AUTH}",
    "AppAuthorization": f"Basic {APP_AUTH}",
    "Content-Type": "application/x-www-form-urlencoded",
}

# --- Data type codes ---
# V.I.T.A.L metric → Thryve code
METRIC_CODES = {
    "heart_rate": 3000,
    "resting_hr": 3001,
    "heart_rate_sleep": 3002,
    "heart_rate_sleep_lowest": 3020,
    "hrv": 3100,
    "hrv_sleep": 3106,
    "hrv_sleep_highest": 3107,
    "sdnn": 3112,
    "spo2": 3009,
    "respiratory_rate": 4000,
    "respiratory_rate_sleep": 4002,
    "vo2_max": 3030,
    "steps": 1000,
    "active_calories": 1011,
    "burned_calories": 1010,
    "distance": 1001,
    "floors_climbed": 1002,
    "workout": 1200,
    "exercise_time": 1100,
    "sleep": 2000,
    "sleep_in_bed": 2001,
    "sleep_deep": 2003,
    "sleep_rem": 2002,
    "sleep_light": 2005,
    "sleep_awake": 2006,
    "body_temperature": 5040,
    "skin_temperature": 5041,
    "weight": 5020,
    "bmi": 5026,
}

# Burnout-relevant analytics codes
BURNOUT_CODES = {
    "average_stress": 6010,
    "high_stress_duration": 6011,
    "medium_stress_duration": 6012,
    "low_stress_duration": 6013,
    "mental_health_risk_sleep": 2254,
    "sick_leave_prediction": 2257,
    "mental_health_risk": 6406,
    "sleep_quality": 2201,
    "sleep_efficiency": 2200,
    "sleep_regularity": 2220,
    "interdaily_stability": 2221,
    "physical_activity_index": 1013,
    "eda": 5050,
}

# Blood biomarker codes
BLOOD_CODES = {
    "blood_glucose": 3302,
    "hba1c": 3303,
    "blood_pressure_diastolic": 3300,
    "blood_pressure_systolic": 3301,
    "estimated_blood_glucose": 3305,
}

# Self-reported wellness (can push back after vocal checkup)
SELF_REPORTED_CODES = {
    "mood": 5115,
    "energy_level": 5117,
    "mental_state": 5125,
    "motivation": 5124,
    "sickness": 5120,
}

# Audio exposure
AUDIO_CODES = {
    "audio_exposure_event": 7100,
    "ambient_audio_exposure": 7101,
    "headphone_audio_exposure": 7102,
}

# Sleep analytics codes
SLEEP_CODES = {
    "sleep_duration": 2000,
    "sleep_rem": 2002,
    "sleep_deep": 2003,
    "sleep_light": 2005,
    "sleep_awake": 2006,
    "sleep_start": 2100,
    "sleep_end": 2101,
    "sleep_latency": 2007,
    "sleep_interruptions": 2102,
    "sleep_quality": 2201,
    "sleep_efficiency": 2200,
    "sleep_regularity": 2220,
}

# Thryve-standardized sleep
THRYVE_MAIN_SLEEP_CODES = {
    "main_sleep_duration": 2300,
    "main_sleep_in_bed": 2301,
    "main_sleep_rem": 2302,
    "main_sleep_deep": 2303,
    "main_sleep_light": 2305,
    "main_sleep_awake": 2306,
    "main_sleep_latency": 2307,
    "main_sleep_start": 2400,
    "main_sleep_end": 2401,
    "main_sleep_interruptions": 2402,
}

# Risk assessment codes
RISK_CODES = {
    "mortality_risk": 2251,
    "cardiovascular_risk": 2252,
    "stroke_risk": 2253,
    "mental_health_risk_sleep": 2254,
    "dementia_risk": 2255,
    "cancer_risk": 2256,
    "sick_leave_prediction": 2257,
    "life_expectancy_impact": 2258,
}

ALL_CODES = {
    **METRIC_CODES, **BURNOUT_CODES, **BLOOD_CODES, **SELF_REPORTED_CODES,
    **AUDIO_CODES, **SLEEP_CODES, **THRYVE_MAIN_SLEEP_CODES, **RISK_CODES,
}

# --- Helpers ---

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _resolve_codes(value_types: str | None) -> str | None:
    """Resolve metric names or raw codes to comma-separated Thryve codes."""
    if not value_types:
        return None
    parts = []
    for part in value_types.split(","):
        part = part.strip()
        if part in ALL_CODES:
            parts.append(str(ALL_CODES[part]))
        else:
            parts.append(part)  # assume raw code
    return ",".join(parts)


async def _post(endpoint: str, data: dict) -> dict | list | str:
    """Make authenticated POST (form-encoded) to Thryve API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{BASE_URL}/{endpoint}",
            headers=HEADERS,
            data=data,
        )
        if r.status_code not in (200, 204):
            return {"error": r.status_code, "body": r.text}
        if r.status_code == 204:
            return {"status": "ok"}
        try:
            return r.json()
        except Exception:
            return r.text


async def _put_json(endpoint: str, body: dict, auth_token: str) -> dict | str:
    """Make authenticated PUT (JSON) to Thryve API."""
    headers = {
        **HEADERS,
        "Content-Type": "application/json",
        "authenticationToken": auth_token,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.put(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            json=body,
        )
        if r.status_code not in (200, 204):
            return {"error": r.status_code, "body": r.text}
        if r.status_code == 204:
            return {"status": "ok"}
        try:
            return r.json()
        except Exception:
            return r.text


async def _delete(endpoint: str, data: dict) -> dict | str:
    """Make authenticated DELETE to Thryve API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request(
            "DELETE",
            f"{BASE_URL}/{endpoint}",
            headers=HEADERS,
            data=data,
        )
        if r.status_code not in (200, 204):
            return {"error": r.status_code, "body": r.text}
        return {"status": "ok"}


# --- MCP Server ---

mcp = FastMCP(
    "thryve",
    instructions=(
        "Thryve Health API — query wearable health data for V.I.T.A.L patients. "
        "Use metric names (heart_rate, hrv, steps, sleep, etc.) or raw Thryve codes. "
        "All data comes from Apple Watch via HealthKit → Thryve."
    ),
)


@mcp.tool()
async def create_user(partner_user_id: str = "") -> str:
    """Create or retrieve a Thryve user token.

    Args:
        partner_user_id: Optional alias for the user (e.g. 'patient-1')

    Returns:
        Authentication token for the user
    """
    data = {}
    if partner_user_id:
        data["partnerUserID"] = partner_user_id
    return await _post("accessToken", data)


@mcp.tool()
async def get_daily_values(
    auth_token: str,
    start_day: str = "",
    end_day: str = "",
    value_types: str = "",
    data_sources: str = "5",
    days_back: int = 7,
) -> dict | list | str:
    """Get daily aggregated health data for a user.

    Args:
        auth_token: User's authentication token from create_user
        start_day: Start date (ISO 8601, e.g. '2026-04-03'). Defaults to days_back ago.
        end_day: End date (ISO 8601). Defaults to today.
        value_types: Comma-separated metric names or Thryve codes.
            Names: heart_rate, resting_hr, hrv, spo2, steps, sleep, etc.
            Codes: 1001, 3001, 2000, etc.
            Empty = all available.
        data_sources: Comma-separated source IDs. Default '5' (Apple Health).
        days_back: How many days back if start_day not set. Default 7.
    """
    data = {
        "authenticationToken": auth_token,
        "startDay": start_day or _days_ago(days_back),
        "endDay": end_day or _today(),
        "displayTypeName": "true",
    }
    resolved = _resolve_codes(value_types)
    if resolved:
        data["valueTypes"] = resolved
    if data_sources:
        data["dataSources"] = data_sources
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_epoch_values(
    auth_token: str,
    start_timestamp: str = "",
    end_timestamp: str = "",
    value_types: str = "",
    data_sources: str = "5",
    hours_back: int = 24,
) -> dict | list | str:
    """Get intraday (epoch) health data with second-level precision.

    Args:
        auth_token: User's authentication token
        start_timestamp: Start datetime (ISO 8601). Defaults to hours_back ago.
        end_timestamp: End datetime (ISO 8601). Defaults to now.
        value_types: Comma-separated metric names or Thryve codes. Empty = all.
        data_sources: Comma-separated source IDs. Default '5' (Apple Health).
        hours_back: Hours back if start_timestamp not set. Default 24.
    """
    now = datetime.now()
    data = {
        "authenticationToken": auth_token,
        "startTimestamp": start_timestamp or (
            (now - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
        "endTimestamp": end_timestamp or now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "displayTypeName": "true",
    }
    resolved = _resolve_codes(value_types)
    if resolved:
        data["valueTypes"] = resolved
    if data_sources:
        data["dataSources"] = data_sources
    return await _post("dynamicEpochValues", data)


@mcp.tool()
async def get_burnout_metrics(
    auth_token: str,
    start_day: str = "",
    end_day: str = "",
    days_back: int = 14,
) -> dict | list | str:
    """Get all burnout-relevant analytics scores for a user.

    Fetches: AverageStress (6010), MentalHealthRisk (2254, 6406),
    SickLeavePrediction (2257), SleepQuality (2201), SleepRegularity (2220),
    InterdailyStability (2221), PhysicalActivityIndex (1013).

    Args:
        auth_token: User's authentication token
        start_day: Start date (ISO 8601). Defaults to days_back ago.
        end_day: End date (ISO 8601). Defaults to today.
        days_back: Days back if start_day not set. Default 14.
    """
    codes = ",".join(str(c) for c in BURNOUT_CODES.values())
    data = {
        "authenticationToken": auth_token,
        "startDay": start_day or _days_ago(days_back),
        "endDay": end_day or _today(),
        "valueTypes": codes,
        "displayTypeName": "true",
    }
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_sleep_analysis(
    auth_token: str,
    start_day: str = "",
    end_day: str = "",
    days_back: int = 7,
    use_standardized: bool = True,
) -> dict | list | str:
    """Get detailed sleep analysis for a user.

    Args:
        auth_token: User's authentication token
        start_day: Start date (ISO 8601). Defaults to days_back ago.
        end_day: End date (ISO 8601). Defaults to today.
        days_back: Days back if start_day not set. Default 7.
        use_standardized: Use ThryveMainSleep codes for cross-device consistency. Default True.
    """
    code_map = THRYVE_MAIN_SLEEP_CODES if use_standardized else SLEEP_CODES
    codes = ",".join(str(c) for c in code_map.values())
    data = {
        "authenticationToken": auth_token,
        "startDay": start_day or _days_ago(days_back),
        "endDay": end_day or _today(),
        "valueTypes": codes,
        "displayTypeName": "true",
    }
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_risk_assessment(
    auth_token: str,
    start_day: str = "",
    end_day: str = "",
    days_back: int = 14,
) -> dict | list | str:
    """Get all sleep-related health risk scores.

    Returns: mortality, cardiovascular, stroke, mental health, dementia,
    cancer, sick leave, and life expectancy risk assessments.

    Args:
        auth_token: User's authentication token
        start_day: Start date. Defaults to days_back ago.
        end_day: End date. Defaults to today.
        days_back: Days back if start_day not set. Default 14.
    """
    codes = ",".join(str(c) for c in RISK_CODES.values())
    data = {
        "authenticationToken": auth_token,
        "startDay": start_day or _days_ago(days_back),
        "endDay": end_day or _today(),
        "valueTypes": codes,
        "displayTypeName": "true",
    }
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_vital_summary(
    auth_token: str,
    days_back: int = 7,
) -> dict | list | str:
    """Get a complete V.I.T.A.L health summary — all 16 mapped metrics.

    Combines vitals, activity, and sleep data in one call.

    Args:
        auth_token: User's authentication token
        days_back: Days of history. Default 7.
    """
    codes = ",".join(str(c) for c in METRIC_CODES.values())
    data = {
        "authenticationToken": auth_token,
        "startDay": _days_ago(days_back),
        "endDay": _today(),
        "valueTypes": codes,
        "displayTypeName": "true",
    }
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_blood_biomarkers(
    auth_token: str,
    start_day: str = "",
    end_day: str = "",
    days_back: int = 30,
) -> dict | list | str:
    """Get blood biomarker data (glucose, HbA1c, blood pressure).

    Sources: CGM devices (Dexcom, FreeStyleLibre), blood pressure monitors.
    Key for Precision Track #1: Wearables + Blood → Daily Coaching.

    Args:
        auth_token: User's authentication token
        start_day: Start date (ISO 8601). Defaults to days_back ago.
        end_day: End date (ISO 8601). Defaults to today.
        days_back: Days back if start_day not set. Default 30.
    """
    codes = ",".join(str(c) for c in BLOOD_CODES.values())
    data = {
        "authenticationToken": auth_token,
        "startDay": start_day or _days_ago(days_back),
        "endDay": end_day or _today(),
        "valueTypes": codes,
        "displayTypeName": "true",
    }
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_stress_detail(
    auth_token: str,
    start_day: str = "",
    end_day: str = "",
    days_back: int = 7,
) -> dict | list | str:
    """Get detailed stress breakdown: average, high/medium/low durations, EDA.

    Args:
        auth_token: User's authentication token
        start_day: Start date. Defaults to days_back ago.
        end_day: End date. Defaults to today.
        days_back: Days back if start_day not set. Default 7.
    """
    codes = ",".join(str(c) for c in [6010, 6011, 6012, 6013, 5050])
    data = {
        "authenticationToken": auth_token,
        "startDay": start_day or _days_ago(days_back),
        "endDay": end_day or _today(),
        "valueTypes": codes,
        "displayTypeName": "true",
    }
    return await _post("dailyDynamicValues", data)


@mcp.tool()
async def get_user_info(auth_token: str) -> dict | list | str:
    """Get user profile and connected data sources.

    Returns height, weight, birthdate, gender, connected wearables.

    Args:
        auth_token: User's authentication token
    """
    return await _post("userInformation", {"authenticationToken": auth_token})


@mcp.tool()
async def update_user_info(
    auth_token: str,
    height: int = 0,
    weight: float = 0,
    birthdate: str = "",
    gender: str = "",
) -> dict | str:
    """Update user profile (improves VO2max, BMI, FitnessAge accuracy).

    Args:
        auth_token: User's authentication token
        height: Height in centimeters (e.g. 175)
        weight: Weight in kilograms (e.g. 72.5)
        birthdate: Date of birth (YYYY-MM-DD)
        gender: 'male', 'female', or 'genderless'
    """
    body = {}
    if height:
        body["height"] = height
    if weight:
        body["weight"] = weight
    if birthdate:
        body["birthdate"] = birthdate
    if gender:
        body["gender"] = gender
    return await _put_json("userInformation", body, auth_token)


@mcp.tool()
async def delete_user(auth_token: str, deletion_date: str = "") -> dict | str:
    """Delete a user (GDPR). Data remains until midnight UTC on deletion date.

    Args:
        auth_token: User's authentication token
        deletion_date: ISO 8601 date. Defaults to 7 days from now.
    """
    data = {"authenticationToken": auth_token}
    if deletion_date:
        data["deletionDate"] = deletion_date
    return await _delete("userInformation", data)


@mcp.tool()
async def get_connection_widget(auth_token: str, locale: str = "fr") -> dict | str:
    """Get URL for the Thryve wearable connection widget (iframe).

    Args:
        auth_token: User's authentication token
        locale: Language code (fr, en, de, es). Default 'fr'.
    """
    headers = {
        **HEADERS,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.thryve.de/widget/v6/connection",
            headers=headers,
            json={"endUserId": auth_token, "locale": locale},
        )
        if r.status_code != 200:
            return {"error": r.status_code, "body": r.text}
        return r.json()


@mcp.tool()
async def list_metric_codes() -> dict:
    """List all available metric names and their Thryve codes.

    Returns a mapping of friendly names to Thryve data type codes,
    organized by category.
    """
    return {
        "core_metrics": METRIC_CODES,
        "burnout_analytics": BURNOUT_CODES,
        "blood_biomarkers": BLOOD_CODES,
        "self_reported": SELF_REPORTED_CODES,
        "audio_exposure": AUDIO_CODES,
        "sleep_analysis": SLEEP_CODES,
        "standardized_sleep": THRYVE_MAIN_SLEEP_CODES,
        "risk_assessment": RISK_CODES,
    }


@mcp.tool()
async def list_data_sources() -> dict:
    """List all Thryve-supported wearable data sources with IDs."""
    return {
        "sources": {
            1: "Fitbit",
            2: "Garmin",
            3: "Polar",
            5: "Apple Health",
            6: "Samsung Health",
            8: "Withings",
            11: "Strava",
            16: "Omron Connect",
            17: "Suunto",
            18: "Oura",
            21: "iHealth",
            27: "Beurer",
            38: "Huawei Health",
            41: "Dexcom",
            42: "Whoop",
            43: "Decathlon",
            44: "Health Connect",
            45: "Komoot",
            46: "FreeStyleLibre",
            47: "ShenAI",
        },
        "default": "5 (Apple Health)",
    }


if __name__ == "__main__":
    mcp.run()
