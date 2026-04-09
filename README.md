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

V.I.T.A.L is a vocal health checkup that crosses what you feel (your voice) with what your body measures (Apple Watch / HealthKit), to detect burnout before it happens.

<p align="center">
  <img src="public/mockups/demo-screenshot-3.png" alt="V.I.T.A.L demo" width="100%">
</p>

→ **You talk** — "How am I doing this week?"
→ **It measures** — HRV, heart rate, sleep, activity from your Watch
→ **It crosses** — "You say you're fine but your HRV dropped from 48 to 22ms"
→ **It acts** — "Want me to book a psychologist? It's covered by your plan."

Works with Apple Watch for full biometric data, or with iPhone Health app alone for users without a Watch.

### Two rituals, no noise

→ **Weekly vocal checkup** — a 2-minute structured conversation that crosses 7 days of biometrics with three subjective questions, producing a burnout score and one concrete action.
→ **Smart daily nudge** — V.I.T.A.L only pings you when your body actually shows a stress signal (HRV drop, short sleep, elevated resting HR). No daily nag. You earn rewards only when listening to your body matters.

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
