---
title: V.I.T.A.L App Design — Medical & Product
created: 2026-04-09
updated: 2026-04-09
type: concept
tags: [vital, implementation, healthkit, mistral, voxtral]
sources:
  - raw/articles/04_vital_app_design.md
---

# V.I.T.A.L App Design

## The Core Problem

Burnout has a **detection gap**: clinical symptoms appear months after physiological degradation. By diagnosis, patient has already lost weeks/months of productivity.

V.I.T.A.L operates in the **pre-burnout window**:

```
Healthy Baseline
      │
      │ ← V.I.T.A.L intervention zone
      ▼
Physiological drift (HRV ↓, Sleep ↓, RHR ↑)
      │
      │ ← Most apps & doctors operate here
      ▼
Subjective symptoms (fatigue, irritability, disengagement)
      │
      ▼
Clinical Burnout (ICD-11 Z73.0)
```

## Weekly Check-In Protocol

### Why Weekly (Not Daily)

Daily check-ins create **self-monitoring fatigue** and increase dropout (Frontiers Public Health 2023). Weekly:
- Reduces burden → better long-term adherence
- Captures 7-day physiological trends
- Aligns with work rhythm (weekly stress accumulation)
- Combined digital+physical outperforms daily-only (PLOS ONE 2025)

### Check-In Structure (~5-7 minutes)

**1. Passive HealthKit Summary** (pre-populated):
- 7-day nocturnal HRV trend vs 4-week baseline
- Avg resting heart rate vs baseline
- Sleep quality composite (deep sleep %, efficiency, duration)
- Active energy/exercise trend, respiratory rate trend

**2. Voxtral Voice Interview** (2-3 min, AI-guided):
- 3 MBI dimensions: exhaustion, cynicism, efficacy
- +2 contextual: recent stressors, recovery activities
- Voice processed locally/server-side with consent → structured score (audio not stored)

**3. AI Synthesis & Risk Score:**
- Composite: physiological drift + subjective report
- Personalized insight citing real numbers
- One recommended micro-action

### Voxtral System Prompt Structure

```
System: You are a compassionate occupational health assistant.
Conduct a brief structured weekly check-in covering:
1. Energy and exhaustion (MBI Dimension 1)
2. Emotional distance from work (MBI Dimension 2)
3. Sense of effectiveness (MBI Dimension 3)
4. Main stressor this week
5. Recovery activity this week
Keep under 3 minutes. Output: JSON with scores 1-5 per dimension + free text summary.
```

## AI Model Architecture

### Input Features

| Feature | Source | Type |
|---|---|---|
| HRV (SDNN, 7-day avg) | HealthKit | Continuous |
| RHR (7-day avg) | HealthKit | Continuous |
| Deep sleep % (7-day) | HealthKit | Continuous |
| Sleep efficiency (7-day) | HealthKit | Continuous |
| Active energy (7-day) | HealthKit | Continuous |
| Respiratory rate (7-day) | HealthKit | Continuous |
| Voxtral MBI proxy score | Voice NLP | 3-dimension ordinal |
| Delta from personal baseline | Computed | Continuous |

### Model Approach

**MVP (hackathon):** Rule-based scoring with clinical thresholds (fast, interpretable, defensible)
- Composite Recovery Deficit Score: weighted z-scores vs 4-week baseline

**Post-MVP:** Bayesian mixed-effects model (proven best for within-person wearable prediction)

### Risk Tiers

| Tier | Color | Criteria | Action |
|---|---|---|---|
| **Optimal** | 🟢 | All within 1 SD of baseline | Maintain, positive reinforcement |
| **Caution** | 🟡 | 1-2 metrics 1-2 SD below baseline | Targeted micro-intervention |
| **Alert** | 🟠 | 2+ metrics >2 SD below OR moderate subjective | Extended check-in, recovery week |
| **High Risk** | 🔴 | 3+ metrics >2 SD AND high subjective | Recommend professional consultation |

## Why Voice Is the Right Medium

1. **Reduced friction:** Speaking faster than typing — critical for fatigued users
2. **Richer signal:** Prosodic features (speech rate, pauses, vocal tone) are validated stress markers
3. **Clinical parallel:** Structured clinical interviews are gold standard (MBI is interviewer-administered)
4. **French language fit:** Voxtral's multilingual essential for French market

## What Makes V.I.T.A.L Medically Defensible

1. Does **not** claim to diagnose — monitors trends and flags risk
2. Uses **validated biomarkers** (HRV, sleep, RHR) with published clinical evidence
3. Uses **validated framework** (Maslach 3 dimensions) for voice check-in
4. Recommends professional consultation at high-risk tiers — amplifies, not replaces healthcare
5. **Personal baseline** more accurate than population thresholds (PMC 2024, 2025)

## Clinical Proof of Concept

**JAMA Network Open (2025)** — Mayo Clinic/Univ. Colorado, 184 physicians RCT:
- Smartwatch use alone (no behavioral prompts) → **54% lower burnout risk at 6 months**
- Higher resilience scores
- **Awareness alone is protective**

This validates V.I.T.A.L's core thesis: giving users visibility into their physiological state prevents burnout.

## Related Pages
- [[healthkit-metrics]] — Input data sources
- [[burnout-physiology]] — What we're detecting
- [[weekly-vocal-checkup]] — User-facing protocol
- [[burnout]] — Clinical definition
- [[hrv]] — Primary biomarker
- [[sleep]] — Central mediator
- [[voice-biomarkers]] — Voice as medium
- [[mistral]] — LLM provider
- [[competitors]] — Market positioning

---
**Status:** Active
**Confidence:** High
