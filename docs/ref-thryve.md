# Thryve Health API -- Dev Reference

> Compiled for V.I.T.A.L hackathon build. Source: [docs.thryve.health](https://docs.thryve.health)

---

## Authentication

Thryve uses **dual Basic Auth** on every request.

| Header | Value | Scope |
|--------|-------|-------|
| `Authorization` | `Basic base64(username:password)` | Global API key |
| `AppAuthorization` | `Basic base64(authID:authSecret)` | Per-app credentials |

Both headers are **required** on every call.

A **per-user token** (`authenticationToken` / `endUserId`) is passed in the **request body** (not a header). You obtain it by calling the Create User endpoint.

### Create / Get User

```
POST https://api.thryve.de/v5/accessToken
Content-Type: application/x-www-form-urlencoded

partnerUserID=<optional-your-alias>
```

Returns plain-text `authenticationToken` (200) or error JSON (400).

---

## Daily Dynamic Values

Aggregated daily data (one value per metric per day).

```
POST https://api.thryve.de/v5/dailyDynamicValues
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <base64>
AppAuthorization: Basic <base64>
```

### Request body

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `authenticationToken` | string | yes | Per-user token |
| `startDay` | string | yes* | ISO 8601 date |
| `endDay` | string | yes* | ISO 8601 date |
| `startTimestampUnix` | int | alt* | Milliseconds |
| `endTimestampUnix` | int | alt* | Milliseconds |
| `valueTypes` | string | no | Comma-separated data type IDs (e.g. `1001,3001`) |
| `dataSources` | string | no | Comma-separated source IDs (e.g. `5`) |
| `detailed` | bool | no | Include recording metadata |
| `displayTypeName` | bool | no | Include human-readable type name |
| `displayPartnerUserID` | bool | no | Include your alias |

*One date pair required. If both ISO and Unix provided, ISO wins.

**Max range: 364 days.**

### Response (200)

```json
[
  {
    "authenticationToken": "abc123",
    "partnerUserID": "user-42",
    "dataSources": [
      {
        "dataSource": 5,
        "data": [
          {
            "day": "2026-04-09",
            "timestampUnix": 1744156800000,
            "createdAt": "2026-04-09T08:00:00Z",
            "createdAtUnix": 1744185600000,
            "dailyDynamicValueType": "1001",
            "dailyDynamicValueTypeName": "Steps",
            "value": "8432",
            "valueType": "LONG",
            "details": {}
          }
        ]
      }
    ]
  }
]
```

### Quick Python example

```python
import httpx, base64

AUTH = base64.b64encode(b"user:pass").decode()
APP_AUTH = base64.b64encode(b"appId:appSecret").decode()

r = httpx.post(
    "https://api.thryve.de/v5/dailyDynamicValues",
    headers={
        "Authorization": f"Basic {AUTH}",
        "AppAuthorization": f"Basic {APP_AUTH}",
    },
    data={
        "authenticationToken": "USER_TOKEN",
        "startDay": "2026-04-03",
        "endDay": "2026-04-10",
        "valueTypes": "1001,3001,2000",
    },
)
data = r.json()
```

---

## Epoch Dynamic Values

Intraday (per-measurement) data with second-level precision.

```
POST https://api.thryve.de/v5/dynamicEpochValues
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <base64>
AppAuthorization: Basic <base64>
```

### Request body

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `authenticationToken` | string | yes | Per-user token |
| `startTimestamp` | string | yes* | ISO 8601 datetime |
| `endTimestamp` | string | yes* | ISO 8601 datetime |
| `startTimestampUnix` | int | alt* | Milliseconds |
| `endTimestampUnix` | int | alt* | Milliseconds |
| `valueTypes` | string | no | Comma-separated data type IDs |
| `dataSources` | string | no | Comma-separated source IDs |
| `detailed` | bool | no | Include recording metadata |
| `displayTypeName` | bool | no | Include type name |
| `displayPartnerUserID` | bool | no | Include alias |

**Max range: 30 days.**

### Response (200)

```json
[
  {
    "authenticationToken": "abc123",
    "dataSources": [
      {
        "dataSource": 5,
        "data": [
          {
            "startTimestamp": "2026-04-09T14:30:00Z",
            "endTimestamp": "2026-04-09T14:31:00Z",
            "startTimestampUnix": 1744209000000,
            "endTimestampUnix": 1744209060000,
            "createdAt": "2026-04-09T14:35:00Z",
            "createdAtUnix": 1744209300000,
            "dynamicValueType": 3001,
            "dynamicValueTypeName": "HeartRate",
            "value": "72",
            "valueType": "LONG",
            "details": {}
          }
        ]
      }
    ]
  }
]
```

Note: `endTimestamp` is `null` for instant measurements (e.g. single heart rate reading).

---

## Data Type Mapping -- V.I.T.A.L to Thryve

### Core 20 metrics

| V.I.T.A.L metric | Thryve code | Thryve name | Endpoint | Value type |
|-------------------|-------------|-------------|----------|------------|
| `heart_rate` | 3001 | HeartRate | epoch | LONG |
| `resting_hr` | 3012 | RestingHeartRate | daily | LONG |
| `hrv` | 3025 | HeartRateVariability | epoch | DOUBLE |
| `spo2` | 3027 | SpO2 | epoch | DOUBLE |
| `respiratory_rate` | 3023 | RespiratoryRate | epoch | DOUBLE |
| `wrist_temperature` | 3029 | WristTemperature | epoch | DOUBLE |
| `vo2_max` | 3030 | VO2max | daily | DOUBLE |
| `walking_hr_avg` | -- | *not available* | -- | -- |
| `steps` | 1001 | Steps | daily | LONG |
| `active_calories` | 1010 | BurnedCalories | daily | LONG |
| `resting_energy` | 1011 | ActiveBurnedCalories | daily | LONG |
| `distance` | 1002 | Distance | daily | DOUBLE |
| `workout` | 1200 | ActivityType | epoch | STRING |
| `stand_time` | -- | *not available* | -- | -- |
| `exercise_time` | 1009 | ExerciseTime | daily | LONG |
| `sleep` | 2000 | SleepDuration | daily | LONG |
| `sleep_deep` | 2003 | SleepDeepDuration | daily | LONG |
| `sleep_rem` | 2002 | SleepREMDuration | daily | LONG |
| `audio_exposure` | -- | *not available* | -- | -- |
| `mindful_minutes` | -- | *not available* | -- | -- |

**4 unmapped metrics** (`walking_hr_avg`, `stand_time`, `audio_exposure`, `mindful_minutes`): These metrics are Apple Health exclusives — not available via Thryve. Omit from MVP or simulate.

### Thryve-standardized sleep (alternative)

Thryve computes its own "main sleep" values that normalize across devices:

| Code | Name |
|------|------|
| 2300 | ThryveMainSleepDuration |
| 2301 | ThryveMainSleepInBedDuration |
| 2302 | ThryveMainSleepREMDuration |
| 2303 | ThryveMainSleepDeepDuration |
| 2305 | ThryveMainSleepLightDuration |
| 2306 | ThryveMainSleepAwakeDuration |
| 2307 | ThryveMainSleepLatency |
| 2400 | ThryveMainSleepStartTime |
| 2401 | ThryveMainSleepEndTime |
| 2402 | ThryveMainSleepInterruptions |

### Additional useful types

| Code | Name | Category |
|------|------|----------|
| 1012 | MetabolicEquivalent | Activity |
| 1013 | PhysicalActivityIndex | Activity (0-45 scale) |
| 1101 | ActivityLowDuration | Activity intensity |
| 1102 | ActivityMidDuration | Activity intensity |
| 1103 | ActivityHighDuration | Activity intensity |
| 1114 | ActiveDuration | Activity |
| 2007 | SleepLatency | Sleep |
| 2100 | SleepStartTime | Sleep |
| 2101 | SleepEndTime | Sleep |
| 2102 | SleepInterruptions | Sleep |
| 2200 | SleepEfficiency | Sleep (0-100) |
| 2201 | SleepQuality | Sleep (0-100) |
| 2220 | SleepRegularity | Sleep (0-100) |
| 3031 | FitnessAge | Cardio |
| 3032 | VO2maxPercentile | Cardio |
| 5020 | Weight | Body |
| 5026 | BMI | Body |

---

## Bonus Analytics -- Burnout-Relevant

Thryve computes derived health risk scores. These are **daily** values.

### Health Risk Assessment

| Code | Name | Description |
|------|------|-------------|
| 2251 | SleepRelatedMortalityRisk | Elevated mortality risk vs. standard population (%) |
| 2252 | SleepRelatedCardiovascularRisk | Elevated cardiovascular disease risk (%) |
| 2253 | SleepRelatedStrokeRisk | Elevated stroke risk (%) |
| **2254** | **SleepRelatedMentalHealthRisk** | **Elevated mental health disease risk (%)** |
| 2255 | SleepRelatedDementiaRisk | Elevated dementia risk (%) |
| 2256 | SleepRelatedCancerRisk | Elevated cancer risk (%) |
| **2257** | **SleepRelatedSickLeavePrediction** | **Estimated increase in sick leave days vs. reference** |
| 2258 | SleepRelatedLifeExpectancyImpact | Estimated years of life lost |

### Mental Health

| Code | Name | Description |
|------|------|-------------|
| **6406** | **MentalHealthRisk** | Binary: no elevated risk or depression risk detected |

### Stress

| Code | Name | Notes |
|------|------|-------|
| 6010 | AverageStress | Referenced in Thryve docs but not found in public pages; may require enterprise access or SDK data. Verify with Thryve team at hackathon. |

**Key for V.I.T.A.L:** Codes `2254` (mental health risk), `2257` (sick leave prediction), and `6406` (mental health binary) are directly relevant to burnout detection. Request these alongside biometric data.

---

## Data Sources

| ID | Source | Type |
|----|--------|------|
| 1 | Fitbit | Web (OAuth) |
| 2 | Garmin | Web (OAuth) |
| 3 | Polar | Web (OAuth) |
| **5** | **Apple Health** | **Native (SDK)** |
| 6 | Samsung Health | Native (SDK) |
| 8 | Withings | Web (OAuth) |
| 11 | Strava | Web (OAuth) |
| 12 | Google Fit REST | Web (EOL) |
| 16 | Omron Connect | Web |
| 17 | Suunto | Web (OAuth) |
| 18 | Oura | Web (OAuth) |
| 21 | iHealth | Web |
| 27 | Beurer | Web |
| 38 | Huawei Health | Native |
| 40 | Google Fit Native | Native (EOL) |
| 41 | Dexcom | Web |
| 42 | Whoop | Web (OAuth) |
| 43 | Decathlon | Web |
| 44 | Health Connect | Native (SDK) |
| 45 | Komoot | Web |
| 46 | FreeStyleLibre | Web |
| 47 | ShenAI | Native |

**For V.I.T.A.L:** Primary source is `5` (Apple Health). Filter all queries with `dataSources=5`.

---

## Data Annotations

Every data point can carry metadata annotations:

| Annotation | Type | Values |
|------------|------|--------|
| `timezoneOffset` | int | Minutes from UTC |
| `generation` | string | `manual_entry`, `manual_measurement`, `automated_measurement`, `smartphone`, `tracker`, `third_party`, `calculation` |
| `medicalGrade` | bool | Whether from a medical device |
| `trustworthiness` | string | `unfavorable_measurement_context`, `doubt_from_device_source`, `doubt_from_user`, `verified_from_device_source`, `verified_from_user` |
| `chronologicalExactness` | int | Minutes of deviation from actual time |

---

## Quick Reference

| What | Value |
|------|-------|
| Base URL | `https://api.thryve.de/v5/` |
| Auth | Dual Basic Auth headers + body token |
| Content-Type | `application/x-www-form-urlencoded` |
| Daily endpoint | `POST /v5/dailyDynamicValues` |
| Epoch endpoint | `POST /v5/dynamicEpochValues` |
| User endpoint | `POST /v5/accessToken` |
| Daily max range | 364 days |
| Epoch max range | 30 days |
| Timestamps | ISO 8601 or Unix milliseconds |
| Apple Health source ID | `5` |
| Value types | `LONG`, `DOUBLE`, `STRING`, `DATE`, `BOOLEAN` |
