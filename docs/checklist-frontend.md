> **⚠️ SUPERSEDED (2026-04-11).** Reflects the pre-pivot weekly-checkup build. Current views + API contract: `HANDOFF.md` (the "Frontend — views to build" and "API contract" sections).

# Frontend Checklist

## Core
- [ ] Browser mic capture → send audio to backend
- [ ] SSE client: consume streaming events from backend
- [ ] Audio playback: play TTS chunks as they stream (don't wait for full response)
- [ ] Works on Chrome/Firefox/Safari, no install

## Screens
- [ ] Checkup screen: mic button + health data cards + burnout gauge + protocol card
- [ ] Patient switcher: dropdown/tabs for 2-3 patients, reload on switch
- [ ] Nudge view: notification card when biometric alert triggers

## SSE Events to Handle
- [ ] emotion → update bear mascot state + label
- [ ] health_data → show metric card (name, value, trend)
- [ ] text → stream LLM response text
- [ ] audio → decode + play PCM audio chunks
- [ ] burnout_score → display score + level
- [ ] protocol → show 3 action cards
- [ ] berries → animate reward
- [ ] done → end loading

## Bear Mascot
- [ ] Render 6 states from designer assets (thinking, curious, concerned, alert, encouraging, happy)
- [ ] Switch on SSE emotion events
- [ ] Show label text (e.g. "Je regarde ton sommeil...")

## Projector Mode
- [ ] Fullscreen, no scrollbars
- [ ] Landscape 16:9 optimized
- [ ] Everything visible in one screen — no scroll

## Mock Mode
- [ ] Hardcoded mock responses to build/test UI without backend
- [ ] Fake SSE stream with delays to simulate real flow

## API Endpoints (backend provides)
- POST /api/checkup/start → { session_id }
- POST /api/checkup/audio → { transcript }
- POST /api/checkup/respond → SSE stream
- GET /api/patients → patient list
- GET /api/patient/{id}/summary → burnout score, protocol, berries
- GET /api/nudge/{patient_id} → nudge if triggered
