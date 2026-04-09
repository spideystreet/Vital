# Apple HealthKit Metrics & Burnout Detection

## Why HealthKit Is Medically Relevant

Apple HealthKit provides **passive, continuous, objective physiological data** — the exact type of data needed to detect the gradual physiological degradation that precedes clinical burnout. The Apple Watch has been validated against medical-grade devices (Polar H7, HealthPatch) with less than 10% error margin on HR and HRV.

> *Source: Apple Watch effectiveness as mental health tracker, PMC 2024 — Hernando et al. (2018) confirmed Apple Watch HRV effectively reflects changes caused by mild mental stress.*

---

## HealthKit Metrics Ranked by Clinical Relevance to Burnout

### Tier 1 — Core Predictors (High Evidence)

#### Heart Rate Variability (HRV) — Nocturnal / Resting
**What it is**: The variation in time between consecutive heartbeats. High HRV = healthy parasympathetic tone (recovery). Low HRV = sympathetic dominance (stress load).

**Clinical relevance**:
- Meta-analysis (PMC NIH, 2018): HRV is a **validated psychological stress indicator** across all populations
- Higher resting HRV associated with more recovery time from work, less mental exhaustion, less fatigue
- Within-person: lower nighttime HRV predicts next-day fatigue, brain fog, and crash events
- Night shift workers have consistently lower HRV → higher burnout risk

**HealthKit key**: `HKQuantityTypeIdentifierHeartRateVariabilitySDNN` (SDNN, 5-minute overnight)

**Interpretation signal for V.I.T.A.L**: A 10–15% sustained drop in personal baseline nocturnal HRV over 2–3 weeks = high-priority alert.

---

#### Resting Heart Rate (RHR)
**What it is**: Heart rate measured during complete rest (usually during sleep).

**Clinical relevance**:
- Elevated RHR at rest = sustained sympathetic activation = chronic stress marker
- Combined with HRV, RHR forms a **recovery score** (parasympathetic/sympathetic balance)
- Wearable models using RHR + HRV show strong predictive performance for stress-related health outcomes

**HealthKit key**: `HKQuantityTypeIdentifierRestingHeartRate`

---

#### Sleep Analysis (Stages + Duration)
**What it is**: Total sleep time, sleep efficiency, deep sleep %, REM %, time to sleep onset.

**Clinical relevance**:
- Deep sleep (slow-wave sleep) is the primary HPA axis recovery window — cortisol clearance happens here
- REM sleep governs emotional regulation — REM disruption is a key early burnout signal
- 14-month study of 775 medical residents: worsening depressive symptoms significantly correlated with **less time in bed and disrupted sleep patterns** (Fitbit Charge 2)
- Bayesian modeling confirmed: every unit increase in daily stress reduces deep sleep proportion the following night

**HealthKit key**: `HKCategoryTypeIdentifierSleepAnalysis` (stages: Core, Deep, REM, Awake — Apple Watch Series 9+ / Ultra)

---

### Tier 2 — Supporting Signals (Moderate Evidence)

#### Respiratory Rate
**What it is**: Breaths per minute, measured during sleep.

**Clinical relevance**:
- Elevated respiratory rate = acute or chronic sympathetic activation
- Under chronic stress, SAM axis increases baseline respiratory rate
- Measurable passively overnight by Apple Watch Series 8+

**HealthKit key**: `HKQuantityTypeIdentifierRespiratoryRate`

---

#### Blood Oxygen Saturation (SpO2)
**What it is**: Oxygen saturation in blood (%), measured at wrist.

**Clinical relevance**:
- Sleep apnea strongly comorbid with burnout (nocturnal desaturation events)
- Persistent SpO2 < 95% during sleep = sleep quality disruption signal
- Indirect burnout marker via sleep fragmentation

**HealthKit key**: `HKQuantityTypeIdentifierOxygenSaturation`

---

#### Active Energy / Steps / Exercise Minutes
**What it is**: Calories burned through activity, step count, workout sessions.

**Clinical relevance**:
- Physical activity protects against burnout by modulating HPA axis reactivity
- **Declining activity is a key early behavioral burnout signal**: burnout patients gradually reduce physical activity before clinical diagnosis
- Bayesian modeling: increased daily active hours → more deep sleep → better HRV recovery
- PLOS Global Public Health (2026): French business leaders at burnout risk showed decreased physical activity alongside poor sleep

**HealthKit keys**: `HKQuantityTypeIdentifierActiveEnergyBurned`, `HKQuantityTypeIdentifierStepCount`

---

#### Wrist Temperature (Body Temperature Variation)
**What it is**: Nightly wrist temperature deviation from personal baseline (Apple Watch Series 8+ / Ultra 2).

**Clinical relevance**:
- Elevated body temperature at night = inflammatory activity (immune response to stress)
- Used by Oura Ring and Apple Watch for illness and ovulation detection — directly applicable to stress load monitoring
- Less studied than HRV but emerging as complementary biomarker

**HealthKit key**: `HKQuantityTypeIdentifierAppleSleepingWristTemperature`

---

### Tier 3 — Contextual / Behavioral Signals

| Metric | HealthKit Key | Burnout Relevance |
|---|---|---|
| Mindful Minutes | `HKCategoryTypeIdentifierMindfulSession` | Protective behavior tracking |
| Stand Hours | `HKCategoryTypeIdentifierAppleStandHour` | Sedentary behavior marker |
| Time in Daylight | `HKQuantityTypeIdentifierTimeInDaylight` | Circadian rhythm regulator |
| Noise Exposure | `HKQuantityTypeIdentifierEnvironmentalAudioExposure` | Workplace stressor proxy |

---

## The Personal Baseline Principle

The clinical literature is clear: **burnout detection requires longitudinal, within-person comparison** — not population thresholds.

A person with baseline HRV of 20ms dropping to 12ms is at higher risk than someone consistently at 15ms. V.I.T.A.L must compute:

```
Personal Baseline (rolling 4-week average)
    → Weekly z-score deviation per metric
    → Composite "Recovery Deficit Score"
    → Risk tier: Green / Amber / Red
```

This is consistent with the BROWNIE study (Mayo Clinic, 2024) protocol, which computes minute-level, daily, weekly, and monthly summaries to capture trend deviations.

---

## Apple Watch Accuracy on Validated Metrics

| Metric | Validation vs. Medical Grade | Error |
|---|---|---|
| Heart Rate | Polar H7 comparison | < 10% |
| HRV (SDNN) | HealthPatch, Empatica E4 | Clinically equivalent for mild stress |
| Sleep Stages | PSG comparison (limited data) | Acceptable for trends, not diagnostic |
| Respiratory Rate | Hospital oximeter | ± 1–2 breaths/min |
| SpO2 | Pulse oximeter | ± 2–3% (FDA cleared, Series 6+) |

> *Sources: Apple Watch mental health tracker review, PMC 2024; Resting HRV Consumer Wearables study, PMC 2025.*

**Key caveat**: Apple Watch metrics are suitable for **population-level trend monitoring and personal baseline deviation detection** — not clinical diagnosis. V.I.T.A.L should position itself as a **preventive early-warning system**, not a diagnostic tool.
