# Thryve Analytics Platform Reference

> Compiled from [docs.thryve.health](https://docs.thryve.health/) -- focused on clinical/burnout-relevant analytics for V.I.T.A.L.

---

## Overview

The Thryve Analytics Platform processes wearable sensor data into health metrics following clinical and scientific best practices in near real-time. It transforms data from hundreds of signals into standardized health insights suitable for healthcare applications, research, and population health monitoring.

Key properties:

- **Continuous computation** -- analytics calculated as new data arrives (milliseconds latency), not batch
- **Clinical foundation** -- built on established clinical frameworks and peer-reviewed research (Fraunhofer Institute spin-off)
- **Multi-device fusion** -- overlap detection, priority-based selection, and deduplication across simultaneous wearables
- **Data harmonization** -- cross-manufacturer metric standardization (critical for sleep data where definitions vary between devices)

---

## Foundational Analytics

These are the base computations that feed into higher-level health assessments. Analytics scores require these as prerequisites.

### Body Composition

| Output | ID | Input Required |
|--------|----|----------------|
| BMI | 5026 | Weight (5020), Height (5030, default 175cm M / 165cm F), Gender (1), Birthyear (10) |
| Waist Circumference | 5027 | Same as BMI |

### Daily Activity Intelligence

Consolidates activity data from multiple sources with overlap detection and deduplication.

| Data Type | ID | Dimension |
|-----------|----|-----------|
| ActiveBinary | 1114 | epoch |
| WalkBinary | 1115 | epoch |
| RunBinary | 1116 | epoch |
| BikeBinary | 1117 | epoch |
| CoveredDistanceWalk/Run/Bike | 1715-1717 | epoch |
| ActiveWalk/Run/BikeDuration | 1825-1827 | epoch |

### Metabolic Equivalent (MET)

| Output | ID | Input Required |
|--------|----|----------------|
| MetabolicEquivalent | 1012 | ActiveBurnedCalories (1011), BurnedCalories (1010), ActivityType (1200), Weight (5020, default 75kg) |
| METmax 1min | 1286 | Rolling peak MET |
| METmax 5min | 1287 | Rolling peak MET |
| METmax 10min | 1288 | Rolling peak MET |
| METmax 60min | 1289 | Rolling peak MET |

Activity intensity classification (daily):
- ActivityLowDuration (1101), ActivityMidDuration (1102), ActivityHighDuration (1103)

### Standardized Sleep Analysis (ThryveMainSleep)

Harmonizes inconsistent sleep definitions across manufacturers. Uses 30-minute interruption threshold to identify the longest continuous sleep cycle.

**Input** (epoch): SleepStateBinary (2000), SleepInBedBinary (2001), REM (2002), Deep (2003), Light (2005), Awake (2006), Snoring (4101)

**Standard Output** (daily):

| Metric | ID |
|--------|----|
| SleepDuration | 2000 |
| SleepREMDuration | 2002 |
| SleepDeepDuration | 2003 |
| SleepLightDuration | 2005 |
| SleepAwakeDuration | 2006 |
| SleepStartTime | 2100 |
| SleepEndTime | 2101 |
| SleepMidTime | 2103 |
| SleepLatency | 2007 |
| SleepAwakeAfterWakeup | 2008 |
| SleepInterruptions | 2102 |

ThryveMainSleep standardized metrics use IDs 2300-2403 (parallel set for cross-device consistency).

---

## Health Status Assessment (Scores)

### Sleep Assessment

| Metric | ID | Scale | Interpretation |
|--------|----|-------|----------------|
| SleepQuality | 2201 | 0-100 | >77 = good sleep quality |
| SleepEfficiency | 2200 | 0-100 | <75 correlates with aging and health conditions |
| SleepRegularity | 2220 | 0-100 | <60 = increased health risks |
| InterdailyStability | 2221 | 0-100 | <50 = irregular daily structure, may indicate mental/neurological issues |

### Physical Activity Index

| Metric | ID | Scale | Interpretation |
|--------|----|-------|----------------|
| PhysicalActivityIndex | 1013 | 0-45 | 0 = inactive, 1-20 = moderate, >20 = highly active |

**Input**: ActivityLowDuration (1101), ActivityMidDuration (1102), ActivityHighDuration (1103), METmax5Min (1287)

### Cardiovascular Fitness

| Metric | ID | Description |
|--------|----|-------------|
| VO2max | 3030 | Maximum oxygen consumption -- strong predictor of cardiovascular and all-cause mortality |
| VO2maxPercentile | 3032 | Age/gender-stratified percentile ranking |
| FitnessAge | 3031 | Age-equivalent fitness level using population norms |

**Input**: PhysicalActivityIndex (1013), heart rate data (resting or sleep), WaistCircumference (5027), Gender, Birthyear

---

## Health Risk Assessment

### Sleep-Related Risk Metrics (daily)

All expressed as elevated risk compared to standard population.

| Code | Metric | Output |
|------|--------|--------|
| **2251** | SleepRelatedMortalityRisk | Elevated mortality risk (%) |
| **2252** | SleepRelatedCardiovascularRisk | Cardiovascular disease risk elevation (%) |
| **2253** | SleepRelatedStrokeRisk | Stroke incidence elevation (%) |
| **2254** | **SleepRelatedMentalHealthRisk** | Elevated risk of developing mental health diseases (%) |
| **2255** | SleepRelatedDementiaRisk | Dementia development probability (%) |
| **2256** | SleepRelatedCancerRisk | Cancer incidence elevation (%) |
| **2257** | **SleepRelatedSickLeavePrediction** | Estimated increase in sick leave days vs. reference population |
| **2258** | SleepRelatedLifeExpectancyImpact | Estimated years lost vs. reference population |

**Input**: Derived from sleep analytics (ThryveMainSleep metrics). Requires wearable sleep tracking data.

### Mental Health Risk Assessment

| Code | Metric | Output |
|------|--------|--------|
| **6406** | MentalHealthRisk | Binary: "No increased risk" or "Increased depression risk identified" |

**Input**: Activity data + sleep data + vital signs + 4 standardized patient-reported clinical questions (validated questionnaire developed with FU Berlin).

### Stress

| Code | Metric | Output |
|------|--------|--------|
| **6010** | AverageStress | Daily stress measurement derived from HRV and activity patterns |

**Input**: Heart rate variability data + activity patterns from wearable.

---

## Burnout-Relevant Codes Summary

These are the codes most relevant to V.I.T.A.L's burnout detection:

| Code | Name | Why It Matters |
|------|------|----------------|
| 6010 | AverageStress | Direct daily stress signal from HRV |
| 2254 | SleepRelatedMentalHealthRisk | Sleep-derived mental health risk % |
| 2257 | SleepRelatedSickLeavePrediction | Predicted excess sick days (burnout proxy) |
| 6406 | MentalHealthRisk | Binary depression risk (requires questionnaire) |
| 2201 | SleepQuality | Sleep quality degradation is early burnout signal |
| 2220 | SleepRegularity | Circadian disruption correlates with burnout |
| 2221 | InterdailyStability | Irregular patterns may indicate mental health issues |
| 1013 | PhysicalActivityIndex | Sedentary behavior amplifies burnout risk |

---

## API Access

### Authentication

Three credential types:

| Credential | Scope |
|------------|-------|
| **Global API Key** | Required for all API requests; consistent across all Thryve apps |
| **App Authentication Keys** | Required for SDK init and API requests; unique per Thryve app/environment |
| **SDK Download Credentials** | For downloading Thryve SDK dependencies |

All credentials are displayed only once and expire 24 hours after email delivery. Store securely.

### Data Delivery Model

Thryve primarily uses a **push model** via webhooks rather than polling:

1. **Data push webhooks** (recommended) -- Thryve pushes data to your endpoint as it arrives
2. **Notification webhooks** -- lightweight notifications that new data is available
3. **Dashboard queries** -- manual data inspection via Thryve dashboard
4. **Health API requests** -- programmatic queries (available for testing with real or mock data)

Webhook configuration:
- Set your endpoint URL in the Thryve dashboard
- Add optional authentication headers
- Choose webhook type (data push vs. notification)
- Test with sample payloads before going live

### Data Dimensions

| Dimension | Granularity | Volume |
|-----------|------------|--------|
| **Epoch** | Seconds-level precision | Up to hundreds of records/day/source/type |
| **Daily** | Calendar-day aggregates in user timezone | One value/source/type/day |

Uniqueness keys:
- Epoch: `dataSourceId` + `thirdPartyDataSourceId` + `dataTypeId` + `startTimestamp` + `generationType`
- Daily: `dataSourceId` + `dataTypeId` + `day`

### Timestamp Formats

- **ISO 8601**: `2025-05-31T09:33:59+01:00` (recommended)
- **Unix milliseconds**: with `timezoneOffset` in minutes to UTC

### Data Annotations (`additionalDetails`)

Every data point can include metadata:

| Field | Type | Values |
|-------|------|--------|
| `generation` | string | `manual_entry`, `manual_measurement`, `automated_measurement`, `smartphone`, `tracker`, `third_party`, `calculation` |
| `medicalGrade` | boolean | `true` = FDA/regulatory certified |
| `trustworthiness` | string | `unfavorable_measurement_context`, `doubt_from_device_source`, `doubt_from_user`, `verified_from_device_source`, `verified_from_user` |
| `chronologicalExactness` | integer | Timestamp precision deviation in minutes |
| `timezoneOffset` | integer | UTC offset in minutes |

---

## Integration Notes for V.I.T.A.L

### Required Wearable Data

To generate burnout-relevant analytics, the following data must flow from the wearable through Thryve:

| Analytics Output | Required Input from Watch |
|------------------|--------------------------|
| AverageStress (6010) | HRV + activity data |
| Sleep scores (2200, 2201, 2220, 2221) | Sleep stages (REM, deep, light, awake) |
| Sleep risk metrics (2254, 2257) | Same sleep data |
| MentalHealthRisk (6406) | Activity + sleep + vitals + 4 questionnaire answers |
| PhysicalActivityIndex (1013) | Activity duration by intensity + MET |
| VO2max (3030) | Activity index + resting HR + body composition |

### Data Flow

```
Wearable → Thryve SDK → Thryve API → V.I.T.A.L backend → Analytics scores
                                                                ↓
                                                    brain.py (LLM context)
```

### Key Considerations

1. **Analytics are computed by Thryve, not locally** -- we send raw data, they return scores
2. **Webhook-first architecture** -- set up webhook endpoint to receive scores as they're computed
3. **Sleep data harmonization** -- Thryve handles Apple Watch sleep stage inconsistencies via ThryveMainSleep
4. **MentalHealthRisk (6406) needs questionnaire** -- the 4 clinical questions could be integrated into the weekly vocal checkup
5. **Fallback values** -- if weight/height unavailable, Thryve uses defaults (75kg, 175cm) which may reduce accuracy
6. **Not diagnostic** -- designed for population health screening and wellness monitoring, aligns with V.I.T.A.L's "no medical diagnosis" constraint
7. **Historic data** -- default 14 days prior to user creation, configurable to 0 for real-time-only

---

*Source: [docs.thryve.health](https://docs.thryve.health/) -- last fetched 2026-04-10*
