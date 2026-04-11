# Thryve API Quickstart for Hackathon Builders

This guide gives you everything you need to fetch end-user health data via the **Thryve Web API** and start building. It is intentionally scoped — no SDKs, no native apps, no webhooks — just the minimum APIs to get from zero to real wearable data fast.

> Full docs (for reference only): https://docs.thryve.health/

> **Stuck on anything or unsure about something? Ping or talk to Amith (amith.joseph@thryve.de) — Product Manager at Thryve, supporting you throughout the hackathon.**

---

## 🚀 Recommended hackathon path: Use pre-made data profiles

**You don't need a wearable to build something cool.** Thryve is providing **pre-made data profiles** — real end-users with rich historical data already sitting in a Thryve app. For each profile you get:

- An `endUserId` (a.k.a. `authenticationToken`) — ready to use, no user creation needed
- A pair of API credentials (`Authorization` + `AppAuthorization`) that can fetch that profile's data

With those two things you can **skip Steps 1 and 2** below entirely and jump straight to **Step 3 — Fetch the data**. This is the fastest path and what we strongly recommend for the hackathon, so you spend your time on your prototype instead of plumbing.

> Profile specs (what data types are available, which sources are connected, date ranges) will be added to this doc once shared. If anything is unclear, ask **Amith (amith.joseph@thryve.de)**.

Steps 1 and 2 (user creation + Connection Widget) are documented below **for completeness only** — skip them unless you specifically want to connect your own wearable.

---

## What is Thryve?

Thryve is a health data aggregation platform that connects to **500+ wearables and health apps** (Fitbit, Garmin, Withings, Oura, Whoop, Polar, Strava, Apple Health, etc.) and exposes a **unified, harmonized API** so you can fetch a user's health data without integrating each vendor individually.

In simpler terms it helps you:

1. Create a Thryve user (get an `endUserId` / `accessToken`).
2. Open the Thryve **Connection Widget** so the user can connect a data source (e.g. Fitbit).
3. Fetch their **epoch data** (high-precision, timestamped) and **daily data** (one value per day).

That's it. But in the interest of time we would we have pre-made data profiles you can use as below highlighted in this google sheets:
https://docs.google.com/spreadsheets/d/1R5Ht6-LfvhZWpVBoRFYVwRTSPl6XlYHMWx1eKVLpogE/edit?gid=0#gid=0

Just use endUserId's from here in API calls + use the provided credentials and you can pull data from the profiles

| Donor Names | Main Source | Other Sources          | Profile Tag                          | EndUserID                        | EndUserAlias                          |
|-------------|-------------|------------------------|--------------------------------------|----------------------------------|---------------------------------------|
| \-          | Withings    |                        | IT Manager                           | a463e0bf26d790d6afdfda0cfd161cf5 | IT-manager-dataprofile                |
| \-          | Whoop       |                        | Active Gym Guy                       | 2bfaa7e6f9455ceafa0a59fd5b80496c | active-workout-dataprofile            |
| \-          | Samsung     | Oura, Withings, Huawei | Moderately active Student in mid 20s | 7f82fc3b0abba3a86b5e15c911fc5f6e | modertate-college-student-dataprofile |
| \-          | Withings    |                        | Our CPO                              | 65b1357f1ceb98f51de05d1cbeb81532 | \-                                    |
| \-          | Apple       |                        | Sedentary Techie 1                   | 1e2e53da12e0a9aebb3750af3c5857e1 | WorkFromHomeTechie                    |
| \-          | Samsung     |                        | Moderate Activity Techie 2           | 26158117728afa6083c58c958eed5d89 | zebra                                 |
| \-          |             |                        |                                      |                                  |                                       |
| \-          | Garmin      |                        | Active Tennis Player                 | eb634efc4ac80c9ed6a355c8a99adb83 | active-garmin-tennis-dataprofile      |
| \-          | Withings    |                        | Senior Profile - Heart Patient       | 79187771a36482f013203b32712e873d | senior-heart-dataprofile              |

## In case if above is not working - contact us or refer google sheets for correct endUserId

## Base URL

Use the QA environment for the hackathon:

```
https://api-qa.thryve.de
```

The Connection Widget is served from:

```
https://connect.qa.thryve.de
```

---

## Authentication

**Every Thryve API call requires TWO headers** (two layers of security):

| Header             | What it is                                                                                  | Format                            |
|--------------------|---------------------------------------------------------------------------------------------|-----------------------------------|
| `Authorization`    | Basic Auth of `username:password` (your partner credentials, think of this like an API key) | `Basic base64(username:password)` |
| `AppAuthorization` | Basic Auth of `authID:authSecret` (identifies your app)                                     | `Basic base64(authID:authSecret)` |

Both (`username:password` for `Authorization`, and `authID:authSecret` for `AppAuthorization`) will be provided to you separately at the start of the hackathon. Use the **same pair of credentials for every API call** described below.

Example headers (for every request):

```http
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
AppAuthorization: Basic YXV0aElEOmF1dGhTZWNyZXQ=
```

---

## The 4-Step Integration Flow(How it works in reality)

```
1. Create Thryve user           →  POST /v5/accessToken
2. Open Connection Widget       →  POST /widget/v6/connection   (embed URL in iframe)
3. User connects a source       →  (handled by widget — Fitbit/Garmin/etc OAuth)
4. Fetch data                   →  POST /v5/dailyDynamicValues
                                →  POST /v5/dynamicEpochValues
```

---

## Step 1 — Create (or retrieve) a Thryve user

All Thryve data is linked to a **Thryve user**, identified by an `endUserId` (also called `accessToken` / `authenticationToken` in v5 — they are the same thing).

You should also set your own alias for the user, called `partnerUserID` (a.k.a. `endUserAlias` in v6 — same thing). This lets you retrieve the same user later.

### Rules for `partnerUserID`

- Must be **unguessable** (e.g. a hash) — minimum **32 chars** recommended
- Allowed chars: digits, letters, `-`
- Max length: **80 chars**
- If you omit it, Thryve creates a brand-new user but you'll have **no way to look them up again**

### Endpoint

```
POST https://api-qa.thryve.de/v5/accessToken
Content-Type: application/x-www-form-urlencoded
```

### Body (form-urlencoded)

| Field           | Required                              | Description                                                                                                                                                         |
|-----------------|---------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `partnerUserID` | optional but **strongly recommended** | Your alias for this user. If a user with this alias already exists, the existing `endUserId` is returned. Otherwise a new user is created and linked to this alias. |

### cURL

```bash
curl --location 'https://api-qa.thryve.de/v5/accessToken' \
  --header 'Authorization: Basic <base64 username:password>' \
  --header 'AppAuthorization: Basic <base64 authID:authSecret>' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'partnerUserID=FVMW6fp9wnUxKnfekrQduZ96Xt6gemVk'
```

### Response

The response body contains the `endUserId` (a hex string), e.g.:

```
85762498eb9e3de75a1a6110b5ddbe83
```

**Save this** `endUserId` — you'll need it for every subsequent call. In v5 endpoints it is passed as `authenticationToken`.

---

## Step 2 — Open the Thryve Connection Widget

The Connection Widget is a Thryve-hosted page that lists all available data sources, lets the user click "Connect" on one (e.g. Fitbit), takes them through the vendor's OAuth login, and redirects them back to your app — all with **zero UI work on your side**.

> ⚠️ **The widget MUST be embedded inside an** `<iframe>` in your web app. Opening it in a new tab/window will break the redirect back to your app.

### Endpoint

```
POST https://api-qa.thryve.de/widget/v6/connection
Content-Type: application/json
```

### Body (JSON)

| Field       | Required | Description                                                                                          |
|-------------|----------|------------------------------------------------------------------------------------------------------|
| `endUserId` | yes      | The `endUserId` returned from Step 1. The data source the user connects will be linked to this user. |

### cURL

```bash
curl --location 'https://api-qa.thryve.de/widget/v6/connection' \
  --header 'Authorization: Basic <base64 username:password>' \
  --header 'AppAuthorization: Basic <base64 authID:authSecret>' \
  --header 'Content-Type: application/json' \
  --data '{
    "endUserId": "85762498eb9e3de75a1a6110b5ddbe83"
  }'
```

### Response

```json
{
  "type": "enduser.widget.connection",
  "data": {
    "url": "https://connect.qa.thryve.de/?connectionSessionToken=1474056721X2441635113203132621&platform=web&lang=en"
  }
}
```

### Embed it

```html
<iframe
  src="https://connect.qa.thryve.de/?connectionSessionToken=...&platform=web&lang=en"
  width="100%"
  height="700"
  style="border:0;">
</iframe>
```

### What happens after the user connects

- Thryve immediately starts ingesting data from that source for this `endUserId`.
- For most sources, Thryve performs a **2-week historical backfill** automatically.
- Data is only stored for data types the user authorized in scope during OAuth.
- From this point on, you can fetch the user's data via the endpoints in Step 3.

> 💡 **Tip for hackathon demos:** After connecting, give it 30–60 seconds before your first fetch — backfill takes a moment.

---

## Step 3 — Fetch the data

There are **two data-fetch endpoints** you'll use. Pick based on what your product needs.

|             | Daily Data                                     | Epoch Data                                                  |
|-------------|------------------------------------------------|-------------------------------------------------------------|
| Endpoint    | `/v5/dailyDynamicValues`                       | `/v5/dynamicEpochValues`                                    |
| Granularity | One value per day per data type                | High-precision timestamped events (down to seconds)         |
| Use it for  | Daily totals, trends, weekly/monthly summaries | Workouts, intraday charts, heart-rate streams, sleep stages |
| Volume      | Small (1 row/day)                              | Large (potentially hundreds/day)                            |
| Date params | `startDay` / `endDay` (`YYYY-MM-DD`)           | `startTimestamp` / `endTimestamp` (ISO 8601)                |
| Max range   | —                                              | **30 days** per request                                     |

> Both endpoints return data **per data source**, grouped inside a `dataSources` array.

---

### 3a. Daily data — `POST /v5/dailyDynamicValues`

Best place to start. One value per day = easy to chart, easy to demo.

#### Endpoint

```
POST https://api-qa.thryve.de/v5/dailyDynamicValues
Content-Type: application/x-www-form-urlencoded
```

#### Body (form-urlencoded)

| Field                  | Required | Description                                                                                   |
|------------------------|----------|-----------------------------------------------------------------------------------------------|
| `authenticationToken`  | yes      | The `endUserId` from Step 1                                                                   |
| `startDay`             | yes      | `YYYY-MM-DD`                                                                                  |
| `endDay`               | yes      | `YYYY-MM-DD`                                                                                  |
| `valueTypes`           | optional | Comma-separated list of data type IDs (e.g. `1000` for Steps). Empty = all available types.   |
| `dataSources`          | optional | Comma-separated list of data source IDs (e.g. `1` for Fitbit). Empty = all connected sources. |
| `detailed`             | optional | `true` to include the `details` annotation object. Recommended: `true`.                       |
| `displayTypeName`      | optional | `true` to include human-readable names like `"Steps"`. Recommended: `true`.                   |
| `displayPartnerUserID` | optional | `true` to echo back your `partnerUserID`.                                                     |

#### cURL

```bash
curl --location 'https://api-qa.thryve.de/v5/dailyDynamicValues' \
  --header 'Authorization: Basic <base64 username:password>' \
  --header 'AppAuthorization: Basic <base64 authID:authSecret>' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'authenticationToken=440dc309e356bc0ac625be596f4e81fd' \
  --data-urlencode 'startDay=2025-01-01' \
  --data-urlencode 'endDay=2025-12-30' \
  --data-urlencode 'valueTypes=1000' \
  --data-urlencode 'detailed=true' \
  --data-urlencode 'displayTypeName=true' \
  --data-urlencode 'displayPartnerUserID=true'
```

#### Sample response (truncated)

```json
[
  {
    "authenticationToken": "440dc309e356bc0ac625be596f4e81fd",
    "partnerUserID": "Thryve-Web-Data-Source-Test-User",
    "dataSources": [
      {
        "dataSource": 18,
        "data": [
          {
            "day": "2025-11-15",
            "createdAt": "2025-11-20T14:07:22Z",
            "dailyDynamicValueType": 1000,
            "dailyDynamicValueTypeName": "Steps",
            "value": "17928",
            "valueType": "LONG",
            "details": {
              "timezoneOffset": 60
            }
          },
          {
            "day": "2025-11-16",
            "createdAt": "2025-11-20T14:07:22Z",
            "dailyDynamicValueType": 1000,
            "dailyDynamicValueTypeName": "Steps",
            "value": "12272",
            "valueType": "LONG",
            "details": { "timezoneOffset": 60 }
          }
        ]
      }
    ]
  }
]
```

#### How to read it

- Top-level array → one entry per user (you only ever query one user, so use `[0]`).
- `dataSources[]` → one entry per connected data source. `dataSource` is the source ID (see table below).
- `data[]` → one entry per day per data type.
- `value` is a **string** — cast to int/float using `valueType` (`LONG` → int, `DOUBLE` → float).
- `details.timezoneOffset` is in **minutes** to UTC.

---

### 3b. Epoch data — `POST /v5/dynamicEpochValues`

Use when you need timestamped/intraday data — heart rate streams, individual workouts, weight measurements, body composition snapshots, etc.

#### Endpoint

```
POST https://api-qa.thryve.de/v5/dynamicEpochValues
Content-Type: application/x-www-form-urlencoded
```

#### Body (form-urlencoded)

| Field                  | Required | Description                                                                                   |
|------------------------|----------|-----------------------------------------------------------------------------------------------|
| `authenticationToken`  | yes      | The `endUserId` from Step 1                                                                   |
| `startTimestamp`       | yes*     | ISO 8601, e.g. `2025-11-01T00:00:00Z`                                                         |
| `endTimestamp`         | yes*     | ISO 8601, e.g. `2025-11-30T00:00:00Z`                                                         |
| `createdAfter`         | yes*     | Alternative to start/end — Unix timestamp; returns everything created/updated after this time |
| `valueTypes`           | optional | Comma-separated data type IDs. Empty = all.                                                   |
| `dataSources`          | optional | Comma-separated data source IDs. Empty = all.                                                 |
| `detailed`             | optional | `true` recommended                                                                            |
| `displayTypeName`      | optional | `true` recommended                                                                            |
| `displayPartnerUserID` | optional | `true` recommended                                                                            |

\* Provide **either** `startTimestamp`+`endTimestamp` **or** `createdAfter`.

#### ⚠️ Critical rules

- **Maximum query range is 30 days.** Requests longer than this will fail or be truncated.
- The response includes any value that **overlaps** with your range. Example: a value spanning `10:00:00–10:04:00` is returned even if you query `10:02:00–10:08:00`.
- For **instant measurements** (weight, single heart-rate reading, body composition, etc.), `endTimestamp` will be the string `"null"`.
- If you accidentally provide both ISO (`startDay`) and Unix params, **ISO wins** and Unix is ignored.

#### cURL

```bash
curl --location 'https://api-qa.thryve.de/v5/dynamicEpochValues' \
  --header 'Authorization: Basic <base64 username:password>' \
  --header 'AppAuthorization: Basic <base64 authID:authSecret>' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'authenticationToken=a798c6ffa7949ad40cf1590643cc129c' \
  --data-urlencode 'startTimestamp=2025-11-01T00:00:00Z' \
  --data-urlencode 'endTimestamp=2025-11-30T00:00:00Z' \
  --data-urlencode 'detailed=true' \
  --data-urlencode 'displayTypeName=true' \
  --data-urlencode 'displayPartnerUserID=true'
```

#### Sample response (trimmed)

```json
[
  {
    "authenticationToken": "a798c6ffa7949ad40cf1590643cc129c",
    "partnerUserID": "01-12-25-Amith-Test",
    "dataSources": [
      {
        "dataSource": 8,
        "data": [
          {
            "startTimestamp": "2025-11-29T05:53:00Z",
            "endTimestamp": "2025-11-29T06:03:00Z",
            "createdAt": "2025-12-01T17:06:08Z",
            "dynamicValueType": 1200,
            "dynamicValueTypeName": "ActivityType",
            "value": "102",
            "valueType": "LONG",
            "details": {
              "generation": "tracker",
              "timezoneOffset": 60
            }
          },
          {
            "startTimestamp": "2025-11-29T10:42:57Z",
            "endTimestamp": "null",
            "createdAt": "2025-12-01T17:04:56Z",
            "dynamicValueType": 5021,
            "dynamicValueTypeName": "MuscleMass",
            "value": "67.22",
            "valueType": "DOUBLE",
            "details": {
              "trustworthiness": "verified_from_device_source",
              "timezoneOffset": 60
            }
          },
          {
            "startTimestamp": "2025-11-27T23:29:32Z",
            "endTimestamp": "null",
            "createdAt": "2025-12-01T17:04:56Z",
            "dynamicValueType": 3009,
            "dynamicValueTypeName": "SPO2",
            "value": "100.0",
            "valueType": "DOUBLE",
            "details": {
              "trustworthiness": "verified_from_device_source",
              "timezoneOffset": 60
            }
          }
        ]
      }
    ]
  }
]
```

#### How to read it

- Same shape as daily data, but each item has `startTimestamp` + `endTimestamp` instead of `day`.
- `endTimestamp = "null"` (literal string) → instant measurement.
- `dynamicValueType` is the data type ID, `dynamicValueTypeName` is the human-readable name.
- `details` carries optional annotations: `generation`, `trustworthiness`, `medicalGrade`, `timezoneOffset`, `chronologicalExactness`. See "Data annotations" below.

---

## Data Source IDs (cheat sheet)

The most useful ones for hackathon demos:

| ID | Source        | Type |
|----|---------------|------|
| 2  | Garmin        | Web  |
| 8  | Withings      | Web  |
| 18 | Oura          | Web  |
| 38 | Huawei Health | Web  |
| 42 | Whoop         | Web  |

Additionally, Samsung and Apple data on profiles via sdk.

> For the hackathon **stick to web data sources**. Native sources (Apple Health, Samsung Health, Health Connect) require the mobile SDK and aren't worth the integration time.

---

## Data Type IDs (`valueTypes`)

The full, up-to-date list of Thryve data type IDs (steps, heart rate, sleep, SpO2, body composition, workouts, etc.) lives in this Airtable:

👉 **https://airtable.com/appUsNn6CVszlBjfw/shroLjZ7pigt4oV7j/tblUI4OiE28Soe8DR**

Use it to look up the `valueTypes` ID for whatever metric your prototype needs.

> Tip: if you're not sure what a data source provides, just call the endpoint with `valueTypes` empty — you'll get everything that exists. Then filter by what you see in the response.
>
> If you can't find a data type or aren't sure whether it's available, ping **Amith (amith.joseph@thryve.de)**.

---

## Data annotations (`details` object)

Both endpoints include a `details` object on every record. The most useful keys:

| Key                      | Type          | Meaning                                                                                                                                                         |
|--------------------------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `timezoneOffset`         | int (minutes) | Offset to UTC. `60` = UTC+1, `-480` = UTC-8                                                                                                                     |
| `generation`             | string        | How the value was produced. Common values: `manual_entry`, `manual_measurement`, `automated_measurement`, `smartphone`, `tracker`, `third_party`, `calculation` |
| `trustworthiness`        | string        | Reliability hint from device/user. e.g. `verified_from_device_source`, `doubt_from_device_source`, `unfavorable_measurement_context`                            |
| `medicalGrade`           | bool          | `true` if recorded by an FDA-equivalent certified device                                                                                                        |
| `chronologicalExactness` | int (minutes) | For daily data, deviation from a 24h day (timezone travel)                                                                                                      |

Use these to filter quality (e.g. drop `manual_entry`, prefer `medicalGrade: true` for clinical use cases).

---

## Daily vs Epoch — quick decision guide

**Use daily data when** you want:

- Step counts per day
- Sleep duration totals
- Calorie totals
- Day-over-day trend lines
- A simple, fast demo

**Use epoch data when** you want:

- Heart rate over time during a workout
- Sleep stages timeline
- Individual weight / body composition entries
- Intraday charts
- Anything that needs precise timestamps

---

---

## Gotchas & tips for hackathon speed

 1. **Always use both auth headers.** Missing `AppAuthorization` is the #1 cause of 401s.
 2. **Embed the widget in an iframe.** Opening it in a new tab silently breaks the redirect.
 3. **Save the** `endUserId` the moment you create a user — you can only look it up later if you also set a `partnerUserID`.
 4. **Wait ~30–60 seconds** after a user connects a source before fetching, to give backfill time to land.
 5. **Epoch queries are capped at 30 days.** Loop in 30-day chunks if you need more.
 6. `value` **is always a string.** Cast it using `valueType` (`LONG` → int, `DOUBLE` → float).
 7. `endTimestamp: "null"` **is a literal string**, not a JSON null. Treat it as "instant measurement".
 8. **No data showing up?** Confirm the user actually authorized the data type during OAuth in the widget — Thryve only stores types the user granted.
 9. **Use Fitbit, Garmin, Withings, Oura, Strava, or Whoop** for the most reliable hackathon demo data.
10. **Skip native SDKs** (Apple Health / Samsung Health / Health Connect) — too much integration overhead for a hackathon.

---

## Optional: Thryve Dashboard (for testing & debugging)

Thryve also provides a **Thryve Dashboard** — a unified web interface to manage Thryve's core products (SDKs and Web APIs). You can use it to configure, manage, and visualize wearable-derived health data from your end users in one place. During the hackathon it's handy for **sanity-checking what data actually exists** for a given profile before you write code against it.

> The Dashboard on its own isn't enough to build — you still need to integrate the Web API (as described above). Think of it as a debugging/visualization companion, not a replacement.

**Want access?** Ask **Amith (amith.joseph@thryve.de)** for Dashboard credentials.

---

## TL;DR

**Fast path (recommended):**

1. Grab a pre-made data profile from Thryve (`endUserId` + credentials)
2. `POST /v5/dailyDynamicValues` for daily aggregates, or `POST /v5/dynamicEpochValues` for high-precision data
3. Build something cool 🚀

**Full path (only if you want to connect your own wearable):**

1. `POST /v5/accessToken` → get `endUserId`
2. `POST /widget/v6/connection` → get widget URL → embed in iframe → user connects a source
3. Fetch as above

**When in doubt, ask Amith — amith.joseph@thryve.de.**

Happy hacking!