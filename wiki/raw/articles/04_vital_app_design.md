# V.I.T.A.L — Medical & Product Design Recommendations

## The Core Problem V.I.T.A.L Solves

Burnout has a **detection gap**: clinical symptoms appear months after the physiological degradation begins. By the time a doctor diagnoses burnout, the patient has already lost weeks or months of productivity and health.

V.I.T.A.L bridges this gap by operating in the **pre-burnout window** — detecting the physiological drift *before* subjective symptoms crystallize.

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

---

## The Weekly Check-In Protocol (Voxtral + HealthKit)

### Why Weekly (Not Daily)

Daily check-ins create **self-monitoring fatigue** and increase dropout rates (systematic review, Frontiers Public Health 2023). Weekly cadence:
- Reduces burden → better long-term adherence
- Captures 7-day physiological trends (more signal than 1-day snapshots)
- Aligns with typical work rhythm (weekly stress accumulation pattern)
- Evidence: digital burnout interventions combining physical + digital sessions outperform daily-only apps (PLOS ONE meta-analysis, 2025)

### The Check-In Structure

A single session of ~5–7 minutes, combining:

1. **Passive HealthKit Summary** (pre-populated, no user effort)
   - 7-day nocturnal HRV trend (vs. personal 4-week baseline)
   - Average resting heart rate (vs. baseline)
   - Sleep quality composite (deep sleep %, sleep efficiency, total duration)
   - Active energy / exercise trend
   - Respiratory rate trend

2. **Voxtral Voice Interview** (2–3 minutes, AI-guided)
   - Structured around 3 MBI dimensions: exhaustion ("How are your energy levels?"), cynicism ("How do you feel about your work this week?"), efficacy ("Did you feel effective?")
   - + 2 contextual questions: recent stressors, recovery activities
   - Voice data processed locally or server-side with consent; output is a structured score (not audio stored)

3. **AI Synthesis & Risk Score**
   - Composite score combining physiological drift + subjective report
   - Personalized insight: "Your HRV dropped 18% this week. You also reported feeling emotionally distant from your work. This combination is an early warning sign."
   - Recommended micro-action (box breathing, sleep time adjustment, activity goal)

---

## The AI Model Architecture

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

For MVP (hackathon):
- **Rule-based scoring** with clinical thresholds (fast to build, interpretable, defensible to medical reviewers)
- Composite Recovery Deficit Score: weighted sum of z-scores per metric vs. personal 4-week baseline

For post-MVP:
- **Bayesian mixed-effects model** (Semantic Scholar, 2025): proven best-in-class for within-person wearable burnout prediction
- Captures individual variability rather than forcing population-level thresholds

### Risk Tiers

| Tier | Color | Criteria | Recommended Action |
|---|---|---|---|
| **Optimal** | 🟢 Green | All metrics within 1 SD of baseline, subjective score low | Maintain — positive reinforcement |
| **Caution** | 🟡 Amber | 1–2 metrics 1–2 SD below baseline OR mild subjective distress | Targeted micro-intervention (sleep hygiene, activity prompt) |
| **Alert** | 🟠 Orange | 2+ metrics > 2 SD below baseline OR moderate subjective distress | Extended check-in, recommend recovery week, manager alert (consent-based) |
| **High Risk** | 🔴 Red | 3+ metrics > 2 SD below baseline AND high subjective score | Recommend professional consultation, generate summary for GP/psychologist |

---

## Voxtral — Why Voice Is the Right Medium

1. **Reduced friction**: Speaking is faster than typing — critical for fatigued users
2. **Richer signal**: Prosodic features (speech rate, pause duration, vocal tone) are validated stress markers in NLP research — Voxtral can extract these beyond text content
3. **Clinical parallel**: Structured clinical interviews are the gold standard for burnout assessment (MBI is interviewer-administered in clinical settings)
4. **French language fit**: Voxtral's multilingual capabilities are essential for the French market

### Suggested Voxtral Prompt Structure

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

---

## What Makes V.I.T.A.L Medically Defensible

1. **It does not claim to diagnose burnout** — it monitors trends and flags risk
2. **It uses validated biomarkers** (HRV, sleep, RHR) with published clinical evidence
3. **It uses a validated conceptual framework** (Maslach 3 dimensions) for its voice check-in
4. **It recommends professional consultation** at high-risk tiers — it amplifies, not replaces, healthcare
5. **Personal baseline approach** is more accurate than population thresholds (supported by PMC 2024, 2025 studies)

---

## Key Scientific References Supporting V.I.T.A.L

| Finding | Study | Relevance |
|---|---|---|
| Smartwatch + self-awareness reduced physician burnout risk by 54% at 6 months | JAMA Network Open, 2025 (Mayo Clinic / Univ. Colorado, 184 physicians RCT) | Core clinical proof of concept |
| Nocturnal HRV and sleep stages = strongest wearable burnout predictors | Semantic Scholar Bayesian model, 2025 | Justifies HRV + sleep as primary metrics |
| Within-person HRV decline predicts mental exhaustion and fatigue | PMC Resting HRV Consumer Wearables, 2025 | Justifies personal baseline approach |
| Digital + physical combined interventions outperform digital-only | PLOS ONE systematic review, 2025 | Justifies human-AI hybrid (Voxtral voice) |
| Apple Watch HRV validated against medical devices for mild stress | PMC Apple Watch mental health review, 2024 | Device validation |
| 53% of French employees report high stress in 2024 (+13 pts) | Ignition Program, 2024 | Market urgency |
