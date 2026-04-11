<p align="center">
  <img src="public/mockups/apple-watch-ultra.png" alt="V.I.T.A.L" width="120">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://mistral.ai"><img src="public/mockups/alanxmistral.png" alt="Alan x Mistral" width="120"></a>
</p>

<h1 align="center">V.I.T.A.L</h1>

<p align="center">
  <strong>Voice-Integrated Tracker & Adaptive Listener</strong><br>
  <em>The first health checkup that listens to how you feel AND measures what your body says.</em>
</p>

<p align="center">
  <img src="https://badgen.net/badge/python/3.12+/3776AB?icon=pypi" alt="Python 3.12+">
  <img src="https://badgen.net/badge/Swift/5.9+/F05138?icon=swift" alt="Swift 5.9+">
  <img src="https://badgen.net/badge/license/MIT/green" alt="License: MIT">
  <img src="https://badgen.net/badge/Apple%20Watch/supported/grey?icon=apple" alt="Apple Watch supported">
</p>

<p align="center">
  <a href="https://mistral.ai"><img src="public/badges/m-orange.svg" alt="Mistral AI" height="32"></a>
  &nbsp;&nbsp;
  <img src="public/badges/apple-health-en.svg" alt="Works with Apple Health" height="32">
</p>

---

> Built for the [**Alan x Mistral AI Health Hack**](https://luma.com/t7rspaka) — April 11, 2026 in Paris.

<img src="public/mockups/alan_X.png" alt="Alan tweet: on a hâte de voir ça" width="560">

## The problem

Absenteeism costs French companies €120B/year. 36% of long-term sick leave is stress and burnout. Companies have no objective way to prevent it — existing health assessments rely on self-reported questionnaires that people fill once and forget.

## The solution

V.I.T.A.L is a **proactive life coach with persistent memory**. It watches your wearable data continuously, remembers your personal patterns, and pushes adaptive daily protocols **before** problems compound into doctor visits.

<p align="center">
  <img src="public/mockups/demo-screenshot-3.png" alt="V.I.T.A.L demo" width="100%">
</p>

→ **It watches** — HRV, heart rate, sleep, activity via Thryve (22 wearable brands)
→ **It remembers** — every event, every protocol, every user-stated goal, stored as append-only markdown
→ **It reaches you** — morning brief + memory-driven notifications, not a dashboard you have to open
→ **It talks to you about you** — *"three weeks ago I saw this exact pattern, the magnesium + zone-2 walk worked in 4 days — let's do that again"*

The differentiator vs dashboard apps (Bevel, Whoop, Oura): persistent memory in the Openclaw / Hermes agent style. Every insight is grounded in the user's own baseline, never population averages.

### Three surfaces, one brain

→ **Morning brief** — the coach initiates. Diagnosis + memory callback + adaptive protocol + one question. Voice via Voxtral TTS, text card in parallel. The user replies and the memory updates live.
→ **Stats dashboard + chat with your data** — each Thryve metric shown with delta vs personal baseline and an LLM insight phrase. Tap a stat to open the chat pre-loaded with that context.
→ **Active notifications** — silent, event-driven. When a biometric deviates ≥2σ from the user's personal baseline, a memory-grounded message pops in — *"3rd time this month after <4h deep sleep, same as mid-March"*.

## Powered by

<table>
  <tr>
    <td align="center"><img src="public/models/mistral-small.png" alt="Mistral Small" width="48"><br><strong>Mistral Small 4</strong><br><sub>Reasoning + Tool Use</sub></td>
    <td align="center"><img src="public/models/voxtral.png" alt="Voxtral" width="48"><br><strong>Voxtral</strong><br><sub>Voice (STT + TTS)</sub></td>
    <td align="center"><img src="public/models/devstral.png" alt="Devstral" width="48"><br><strong>Devstral</strong><br><sub>Code companion</sub></td>
  </tr>
</table>

## Health metrics

20 metrics across 5 categories — vitals, activity, sleep, environment, mindfulness.  
See [docs/health-metrics.md](docs/health-metrics.md) for the full dictionary.

## Privacy

Zero personal identifiers sent to the LLM — only anonymous aggregated metrics.  
See [docs/privacy-rgpd.md](docs/privacy-rgpd.md).

## License

MIT
