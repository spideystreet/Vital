# Apple Shortcut Setup — V.I.T.A.L Health Sync

This shortcut reads your Apple Watch health data from HealthKit and POSTs it
to the V.I.T.A.L server running on your Mac.

## Prerequisites

- iPhone with Apple Health data (Apple Watch paired)
- V.I.T.A.L server running on your Mac (`uv run python -m vital.health_server`)
- Both devices on the same local network
- Your Mac's local IP (find it in System Settings → Wi-Fi → Details → IP Address)

## Server URL

```
http://<YOUR_MAC_IP>:8420/health
```

Example: `http://192.168.1.42:8420/health`

> Tip: assign a static IP to your Mac or use its `.local` hostname
> (e.g. `http://macbook.local:8420/health`)

---

## Shortcut Blueprint — step by step

Open the **Shortcuts** app on your iPhone and create a new shortcut named
**"VITAL Sync"**.

### Step 1 — Set your server URL

| Action | Config |
|--------|--------|
| **Text** | `http://<YOUR_MAC_IP>:8420/health` |
| Set variable | Name: `server_url` |

---

### Step 2 — Heart Rate (last 1h)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Heart Rate** |
| | Start Date: 1 hour ago |
| | Sort by: **Start Date** (Latest First) |
| | Limit: **10** |

---

### Step 3 — Resting Heart Rate (today)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Resting Heart Rate** |
| | Start Date: Start of Today |
| | Sort by: **Start Date** (Latest First) |
| | Limit: **1** |

---

### Step 4 — Blood Oxygen / SpO2 (last 24h)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Blood Oxygen** |
| | Start Date: 1 day ago |
| | Sort by: **Start Date** (Latest First) |
| | Limit: **5** |

---

### Step 5 — Steps (today)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Steps** |
| | Start Date: Start of Today |
| | Group by: **Day** |
| | Limit: **1** |

---

### Step 6 — Active Calories (today)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Active Energy** |
| | Start Date: Start of Today |
| | Group by: **Day** |
| | Limit: **1** |

---

### Step 7 — Heart Rate Variability / HRV (last 24h)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Heart Rate Variability** |
| | Start Date: 1 day ago |
| | Sort by: **Start Date** (Latest First) |
| | Limit: **5** |

---

### Step 8 — Sleep Analysis (last night)

| Action | Config |
|--------|--------|
| **Find Health Samples** | Type: **Sleep Analysis** |
| | Start Date: 1 day ago |
| | Sort by: **Start Date** (Latest First) |
| | Limit: **1** |

---

### Step 9 — Build JSON payload

| Action | Config |
|--------|--------|
| **Dictionary** | (see JSON structure below) |

Build a **Dictionary** with key `metrics` containing a **List** of items.
Each item is a dictionary:

```json
{
  "metric": "<metric_name>",
  "value": <Health Sample.Value>,
  "unit": "<unit>",
  "recorded_at": "<Health Sample.Start Date (ISO 8601)>"
}
```

For each Find Health Samples result, use **Repeat with Each** to add entries.

> Use the **Dictionary** action to build the JSON structure. Avoid using the **Text** action for JSON construction, as it can lead to formatting issues.

---

### Step 10 — POST to V.I.T.A.L

| Action | Config |
|--------|--------|
| **Get Contents of URL** | URL: `server_url` variable |
| | Method: **POST** |
| | Headers: `Content-Type: application/json` |
| | Request Body: **File** → the Text/Dictionary from Step 9 |

---

### Step 11 (optional) — Show result

| Action | Config |
|--------|--------|
| **Show Result** | Contents of URL |

This shows the server's response (`{"status": "ok", "inserted": 7}`) as
confirmation.

---

## Automation (hands-free sync)

To run automatically:

1. Open **Shortcuts** → **Automation** tab
2. Tap **+** → **Create Personal Automation**
3. Choose a trigger:
   - **Time of Day** → e.g. every morning at 7:00 AM
   - **When I arrive/leave** a location
   - **When I open an app** (e.g. open Health app)
4. Action: **Run Shortcut** → select **VITAL Sync**
5. Toggle OFF **"Ask Before Running"**

Recommended: run every morning + every evening for good coverage.

---

## Metric name reference

| Shortcut metric | `metric` field | `unit` |
|----------------|----------------|--------|
| Heart Rate | `heart_rate` | `bpm` |
| Resting Heart Rate | `resting_heart_rate` | `bpm` |
| Blood Oxygen | `spo2` | `%` |
| Steps | `steps` | `count` |
| Active Energy | `calories` | `kcal` |
| Heart Rate Variability | `hrv` | `ms` |
| Sleep Analysis | `sleep` | `hours` |

---

## iOS Health Permissions Setup

Before running the shortcut, ensure that the Shortcuts app has permission to access Health data:

1. Open the **Health** app on your iPhone.
2. Tap your profile picture → **Apps** → **Shortcuts**.
3. Enable all relevant permissions (Heart Rate, Blood Oxygen, Steps, etc.).

## Troubleshooting

- **"Could not connect"** → check that the server is running and both devices are on the same Wi-Fi
- **"Request timeout"** → check your Mac's firewall settings (System Settings → Firewall → allow Python)
- **No data found** → make sure your Apple Watch has synced recent data to iPhone (open Health app first)
- **Test with ping** → try `http://<YOUR_MAC_IP>:8420/health/ping` in Safari first
- **"Action trying to share N items" error** → This occurs when the shortcut tries to process multiple items incorrectly. Ensure that each **Find Health Samples** action is followed by a **Repeat with Each** action to handle the list of samples correctly.
