---
title: Weekly Vocal Check-up
created: 2026-04-07
updated: 2026-04-09
type: concept
tags: [voice-biomarker, implementation, ritual, mistral, voxtral]
sources:
  - alan_pressroom.md
  - raw/articles/04_vital_app_design.md
---

# Weekly Vocal Check-up

## Concept

**What:** A ~5–7 minute structured voice conversation, once a week, crossing subjective state (MBI 3 dimensions via Voxtral) with objective HealthKit data (HRV, sleep, resting HR, exercise) → produce a Recovery Deficit Score and one concrete recommendation.

**Why:** Alan Play shows 26% weekly engagement on gamified prevention — a weekly ritual is the proven cadence. Daily is too noisy for HRV/sleep trends and increases dropout (Frontiers Public Health, 2023). Weekly captures 7-day accumulation patterns.

**When:** Sunday evening or Monday morning by default. Push notification from Watch.

## Why Weekly (Not Daily)

- Daily check-ins → self-monitoring fatigue → higher dropout
- Weekly captures 7-day physiological trends (more signal than 1-day snapshots)
- Aligns with typical work rhythm (weekly stress accumulation)
- Digital + physical combined interventions outperform daily-only (PLOS ONE meta-analysis, 2025)

## The Check-In Structure

### 1. Passive HealthKit Summary (pre-populated)
- 7-day nocturnal HRV trend vs 4-week baseline
- Avg resting heart rate vs baseline
- Sleep quality composite (deep sleep %, efficiency, duration)
- Active energy / exercise trend, respiratory rate trend

### 2. Voxtral Voice Interview (2–3 min)

Structured around 3 MBI dimensions + 2 contextual:

| Question | MBI Dimension |
|---|---|
| "How are your energy levels this week?" | Exhaustion |
| "How do you feel about your work right now?" | Cynicism |
| "Did you feel effective/accomplished?" | Efficacy |
| "What stressed you most this week?" | Contextual |
| "Did you have time to recover?" | Contextual |

### 3. AI Synthesis & Risk Score

- Composite score: physiological drift + subjective report
- Personalized insight: "Your HRV dropped 18% this week. You also reported feeling emotionally distant from your work. This combination is an early warning sign."
- One recommended micro-action (breathing, sleep time adjustment, activity goal)

## Risk Tiers

| Tier | Color | Criteria | Action |
|---|---|---|---|
| **Optimal** | 🟢 | All within 1 SD of baseline | Maintain, positive reinforcement |
| **Caution** | 🟡 | 1–2 metrics 1–2 SD below OR mild subjective | Targeted micro-intervention |
| **Alert** | 🟠 | 2+ metrics >2 SD below OR moderate subjective | Extended check-in, recovery week |
| **High Risk** | 🔴 | 3+ metrics >2 SD AND high subjective | Recommend professional consultation |

## Voxtral Prompt Structure

```
System: You are a compassionate occupational health assistant.
Conduct a brief structured weekly check-in covering:
1. Energy and exhaustion (MBI Dimension 1)
2. Emotional distance from work (MBI Dimension 2)  
3. Sense of effectiveness (MBI Dimension 3)
4. Main stressor this week
5. Recovery activity this week

Keep the conversation natural, under 3 minutes.
Output: JSON with scores 1-5 per dimension + free text summary.
```

## Engagement Strategy
- **Streak:** count consecutive weekly checkups completed (see [[gamification]])
- **Trend card:** show score evolution week-over-week on iPhone app
- **Alan integration:** weekly completion could earn Alan Play berries

## Implementation Notes
- New mode in `vital/brain.py`: `weekly_checkup` flag → LLM switches from reactive Q&A to structured 3-question script
- `get_health_trend` and `get_health_summary(168)` mandatory at step 1
- Score: weighted formula in Python (not LLM-generated) for reproducibility

## Related Pages
- [[voice-biomarkers]] — Technical basis
- [[gamification]] — Engagement layer
- [[hrv]] — Primary biomarker
- [[sleep]] — Secondary biomarker
- [[burnout]] — What we're detecting
- [[healthkit-metrics]] — Input data
- [[vital-app-design]] — Full app architecture
- [[alan]] — Weekly engagement benchmark (26%)

---
**Status:** Updated with full protocol and risk tiers
**Confidence:** High
