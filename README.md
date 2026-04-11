<p align="center">
  <img src="public/mockups/apple-watch-ultra.png" alt="V.I.T.A.L" width="120">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://mistral.ai"><img src="public/mockups/alanxmistral.png" alt="Alan x Mistral" width="120"></a>
</p>

<h1 align="center">V.I.T.A.L</h1>

<p align="center">
  <strong>Voice-Integrated Tracker & Adaptive Listener</strong><br>
  <em>The first proactive health coach that actually remembers you.</em>
</p>

<p align="center">
  <img src="https://badgen.net/badge/python/3.12+/3776AB?icon=pypi" alt="Python 3.12+">
  <img src="https://badgen.net/badge/voice/Voxtral/F05138" alt="Voice: Voxtral">
  <img src="https://badgen.net/badge/brain/Mistral%20Small/FF7000" alt="Brain: Mistral Small">
  <img src="https://badgen.net/badge/license/MIT/green" alt="License: MIT">
</p>

<p align="center">
  <a href="https://mistral.ai"><img src="public/badges/m-orange.svg" alt="Mistral AI" height="32"></a>
  &nbsp;&nbsp;
  <a href="https://luma.com/t7rspaka"><img src="public/mockups/alanxmistral.png" alt="Alan × Mistral Hackathon" height="32"></a>
</p>

---

> Built for the [**Alan × Mistral AI Health Hack**](https://luma.com/t7rspaka) — April 11, 2026, Paris.

<p align="left">
  <img src="public/mockups/alan_X.png" alt="Alan tweet: on a hâte de voir ça" width="480">
</p>

## Why

Burnout drains **€120B/year** from French companies. 36% of long-term sick leave is stress-related. Every health app shows you a dashboard. **None of them know you.**

V.I.T.A.L reads your wearable, learns *your* baselines, and pushes adaptive protocols **before** problems become doctor visits.

<p align="center">
  <img src="public/mockups/img1alan.png" alt="V.I.T.A.L demo" width="100%">
</p>

## What it does

→ 🗣️ **Proactive morning brief** — it starts the conversation, voice-first, with a memory callback: *"3rd time this month after <4h deep sleep, same as mid-March."*  
→ 💬 **Chat with your data** — tap any stat, the LLM explains the delta vs **your** baseline — never population averages.  
→ 🔔 **Silent nudges** — pings only when your biometric drifts ≥2σ from your own baseline.  
→ 🎙️ **Vocal onboarding** — free-speech form filling. Talk once, your dossier fills itself across 5 categories.  
→ 📄 **Blood panel OCR** — drop a PDF, get 16 biomarkers extracted in seconds.  
→ 🏥 **Specialist booking** — need an ORL? The coach books it. Alan-covered, 100% reimbursed.  
→ 🎯 **Personalized challenges** — targets calibrated on *your* baseline, not generic 10k steps.  

## The differentiator

**Persistent memory** in the Openclaw / Hermes agent pattern. Every insight is grounded in the user's own history — `Baselines`, `Events`, `Protocols`, `Context`, `Challenges`, `Bookings` — all as append-only markdown the LLM reads and writes via function calls.

```
  Dashboard apps              V.I.T.A.L
  ─────────────────          ─────────────────
  "Your HRV is 45ms"    →    "Your HRV is 14% below your 14-day
                              baseline. Last time this happened,
                              zone-2 + magnesium fixed it in 4 days."
```

<p align="center">
  <img src="public/mockups/Alan_image1.png" alt="V.I.T.A.L x Alan" width="100%">
</p>

## Powered by

<table>
  <tr>
    <td align="center"><img src="public/models/mistral-small.png" alt="Mistral Small" width="48"><br><strong>Mistral Small</strong><br><sub>Reasoning + 10 tools</sub></td>
    <td align="center"><img src="public/models/voxtral.png" alt="Voxtral" width="48"><br><strong>Voxtral</strong><br><sub>STT + streaming TTS</sub></td>
    <td align="center"><img src="public/models/devstral.png" alt="Devstral" width="48"><br><strong>Mistral OCR</strong><br><sub>Blood panel parsing</sub></td>
  </tr>
</table>

## Stack

`FastAPI` · `Mistral Small` + 10 function-calling tools · `Voxtral` STT/TTS · `Mistral OCR` · `Nebius Llama Guard` safety · `Thryve` (22 wearables, 20 metrics) · `Expo` mobile

## Privacy

Zero personal identifiers sent to the LLM — only anonymous aggregated metrics. See [docs/privacy-rgpd.md](docs/privacy-rgpd.md).

## License

MIT
