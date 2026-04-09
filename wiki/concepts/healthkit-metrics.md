---
title: HealthKit Metrics for Burnout Detection
created: 2026-04-09
updated: 2026-04-09
type: concept
tags: [healthkit, biomarker, hrv, sleep, metric]
sources:
  - raw/assets/02_healthkit_metrics.md
  - raw/docs/healthkit.md
---

# HealthKit Metrics for Burnout Detection

Apple HealthKit provides **passive, continuous, objective physiological data** — the exact type needed to detect gradual burnout degradation. Apple Watch validated against medical-grade devices (Polar H7, HealthPatch) with <10% error on HR/HRV.

## Tier 1 — Core Predictors (High Evidence)

### HRV (Nocturnal / Resting)
- **HealthKit key:** `HKQuantityTypeIdentifierHeartRateVariabilitySDNN` (SDNN, 5-minute overnight)
- High = healthy parasympathetic tone. Low = sympathetic dominance.
- Meta-analysis (PMC 2018): validated psychological stress indicator across populations
- Within-person: lower nighttime HRV predicts next-day fatigue, brain fog
- **V.I.T.A.L signal:** 10–15% sustained drop in personal baseline over 2–3 weeks = high-priority alert

### Resting Heart Rate (RHR)
- **HealthKit key:** `HKQuantityTypeIdentifierRestingHeartRate`
- Elevated RHR at rest = sustained sympathetic activation = chronic stress
- Combined with HRV forms a recovery score (parasym/symp balance)

### Sleep Stages + Duration
- **HealthKit key:** `HKCategoryTypeIdentifierSleepAnalysis` (Core, Deep, REM, Awake — AW Series 9+)
- Deep sleep = HPA axis recovery, cortisol clearance
- REM = emotional regulation, disruption = early burnout signal
- 14-month study (775 residents): depressive symptoms correlated with less time in bed
- **<7h = 17x burnout odds (women), 8x (men)** — [[sleep]]

## Tier 2 — Supporting Signals (Moderate Evidence)

| Metric | HealthKit Key | Signal |
|---|---|---|
| Respiratory Rate | `HKQuantityTypeIdentifierRespiratoryRate` | Elevated = sympathetic activation |
| SpO2 | `HKQuantityTypeIdentifierOxygenSaturation` | Sleep apnea comorbidity |
| Active Energy / Steps | `HKQuantityTypeIdentifierActiveEnergyBurned`, `StepCount` | Declining = early behavioral signal |
| Wrist Temperature | `HKQuantityTypeIdentifierAppleSleepingWristTemperature` | Nightly deviation from baseline, inflammatory proxy |

## Tier 3 — Contextual

| Metric | HealthKit Key | Signal |
|---|---|---|
| Mindful Minutes | `HKCategoryTypeIdentifierMindfulSession` | Protective behavior |
| Stand Hours | `HKCategoryTypeIdentifierAppleStandHour` | Sedentary marker |
| Time in Daylight | `HKQuantityTypeIdentifierTimeInDaylight` | Circadian regulator |
| Noise Exposure | `HKQuantityTypeIdentifierEnvironmentalAudioExposure` | Workplace stressor proxy |

## Device Accuracy

| Metric | Validation | Error |
|---|---|---|
| Heart Rate | vs Polar H7 | < 10% |
| HRV (SDNN) | vs HealthPatch, E4 | Clinically equivalent for mild stress |
| Sleep Stages | vs PSG (limited) | Acceptable for trends, not diagnostic |
| Respiratory Rate | vs hospital oximeter | ± 1–2 breaths/min |
| SpO2 | vs pulse oximeter | ± 2–3% (FDA cleared, Series 6+) |

## The Personal Baseline Principle

**Burnout detection requires longitudinal, within-person comparison — not population thresholds.**

A person with baseline HRV of 20ms dropping to 12ms is at higher risk than someone consistently at 15ms:

```
Personal Baseline (rolling 4-week average)
    → Weekly z-score deviation per metric
    → Composite "Recovery Deficit Score"
    → Risk tier: Green / Amber / Red
```

Consistent with BROWNIE study (Mayo Clinic, 2024) protocol.

> **Caveat:** Apple Watch suitable for preventive early-warning, not clinical diagnosis.

## Related Pages
- [[burnout-physiology]] — Why these metrics matter physiologically
- [[hrv]] — Deep dive on HRV as stress biomarker
- [[sleep]] — Sleep-burnout link
- [[weekly-vocal-checkup]] — How metrics feed the checkup
- apple — Device capabilities

---
**Status:** Active
**Confidence:** High
