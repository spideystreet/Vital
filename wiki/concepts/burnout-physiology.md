---
title: Burnout Physiology — HPA & SAM Axes
created: 2026-04-09
updated: 2026-04-09
type: concept
tags: [burnout, biomarker, clinical-study, paper]
sources:
  - raw/papers/01_burnout_physiology.md
  - raw/articles/03_france_market.md
---

# Burnout Physiology

## What Burnout Is — Clinically

WHO ICD-11 (2022, code **Z73.0**): occupational phenomenon from chronic workplace stress not successfully managed.

Three dimensions (assessed via **Maslach Burnout Inventory, MBI**):
1. **Exhaustion** — depleted energy, persistent fatigue
2. **Cynicism/Depersonalization** — mental distance from job, negativity toward work
3. **Reduced professional efficacy** — loss of confidence in performance

## The Root Mechanism: Two Stress Axes

### 1. HPA Axis (Hypothalamic–Pituitary–Adrenal)

The hormonal stress response:
1. Hypothalamus → CRH
2. Pituitary → ACTH
3. Adrenal cortex → **Cortisol**

Cortisol normally peaks at awakening (CAR), dips at night. Under chronic stress:
- **Elevated or blunted CAR** — both signs of HPA dysregulation
- Hair cortisol = most reliable chronic stress biomarker (9-study systematic review, ICA Health 2022)
- Burnout patients show elevated awakening cortisol

### 2. SAM Axis (Sympatho-Adrenomedullary)

Fast neurological fight-or-flight:
- Increases: HR, blood pressure, respiratory rate
- **Decreases: HRV** — our primary measurable signal
- Sympathetic overload persists even at rest under chronic stress

## The Burnout Cascade

```
Chronic work stressor
        │
        ▼
Repeated HPA + SAM activation
        │
        ▼
Cortisol dysregulation + sympathetic overload
        │
        ├──► Sleep disruption (reduced deep sleep, fragmented recovery)
        ├──► Immune suppression (inflammatory markers rise)
        ├──► HRV suppression (reduced parasympathetic recovery)
        └──► Progressive exhaustion → Cynicism → Efficacy loss
                        │
                        ▼
                   BURNOUT (ICD-11 Z73.0)
```

## Key Physiological Biomarkers

| Biomarker | Axis | Measurable by Apple Watch? | Burnout Link |
|---|---|---|---|
| **HRV (nocturnal)** | ANS / SAM | ✅ | Lower = higher stress load |
| **Resting Heart Rate** | SAM | ✅ | Elevated = sympathetic dominance |
| **Sleep stages** | CNS / HPA | ✅ | Reduced deep sleep = HPA overdrive |
| **Respiratory Rate** | SAM | ✅ (AW Series 8+) | Elevated = stress marker |
| **Blood Oxygen (SpO2)** | CNS | ✅ | Sleep apnea comorbidity |
| **Physical activity** | Behavioral | ✅ | Declining = early signal |
| **Cortisol (hair/saliva)** | HPA | ❌ Lab only | Gold-standard chronic marker |

## Sleep as the Central Mediator

- Elevated cortisol + sympathetic activity → **reduce sleep quality directly**
- Chronic insomnia → **24h hypersecretion of ACTH/cortisol** → feedback loop
- **Reduced deep sleep → reduced HRV recovery** → further sympathetic dominance
- Bayesian modeling (2025): **nocturnal HRV + sleep stage proportions = two strongest wearable predictors**
- Deep sleep (slow-wave) = primary HPA axis recovery, cortisol clearance
- REM sleep = emotional regulation, disruption = early burnout signal

## The Wearable Evidence Gap

A systematic review of 10 wearable studies (PMC 2024):
- **No single metric predicts MBI burnout in short (2-4 week) cross-sectional studies**
- **Longitudinal tracking (months) shows stronger associations**
- **Within-person analysis is more sensitive** than between-person comparison
- Personal baselines matter more than population norms

This reinforces V.I.T.A.L's **weekly, longitudinal, AI-personalized approach**.

> *Sources: Frontiers in Psychology (2025), Semantic Scholar narrative review (2025), PMC 2024 systematic review, ICA Health (2022)*

See [[scientific-references]] for full bibliography with links.

## Related Pages
- [[burnout]] — What we're tracking
- [[hrv]] — SAM axis signal via wearables
- [[sleep]] — Central mediator
- [[apple]] — Device accuracy
- Competitors
- Scientific References

---
**Status:** Active
**Confidence:** High
