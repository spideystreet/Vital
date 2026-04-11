# Skill: Update Docs

## Which docs to update

- `.vibe/CONTEXT.md` — Vibe's view of the project. Update when code structure changes.
- `docs/ARCHITECTURE.md` — current system diagram, endpoints, tools. Update when surfaces or modules change.
- `HANDOFF.md` — team-facing handoff. Update when API contract, SSE events, or demo script change.
- `docs/privacy-rgpd.md` — privacy doc. Update when data flow changes.

## Rules

- Keep the **proactive coach** framing — V.I.T.A.L is a life coach with persistent memory, not a dashboard
- Never modify `CLAUDE.md` — that's Claude Code's domain
- Never modify `.claude/` files
- Never modify historical docs marked SUPERSEDED (plan-hackathon.md, checklist-*.md) — they are frozen
- Match the existing tone and format of each doc
- English for code docs, French allowed for pitch-facing docs
- Keep docs concise — no filler, no redundancy

## When updating CONTEXT.md / ARCHITECTURE.md / HANDOFF.md

- Verify the tool count (currently **9 tools** in `brain.py`, including `read_memory` + `append_memory`)
- Verify the 3 surfaces are described: morning brief, dashboard + chat, silent notifications
- Check that memory is described as append-only markdown per Thryve endUserId in `data/memory/`
- Verify endpoints list matches `health_server.py`: `/api/coach/brief`, `/api/coach/reply`, `/api/dashboard/{patient_id}`, `/api/notifications/stream`, `/dev/fire-notification`
- Mention that FastAPI auto-exposes Swagger UI at `/docs` and `/openapi.json`
- Never reference removed modules: `health_store.py`, `berries.py`, `voice_ws.py`

## After updating

- Read the file back to verify formatting
- Run `uv run ruff check backend/` to ensure no code was accidentally modified
