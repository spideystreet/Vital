# Vital

> Finally, your health data works for you.

## Project structure

```
backend/           # Python REST API (FastAPI) — not yet scaffolded
ios/               # Swift iOS app (SwiftUI) — not yet scaffolded
docs/              # Mintlify documentation
public/            # Static assets (badges, mockups, model logos)
```

## Commands

```bash
# Documentation (requires Node 22)
cd docs && npx mintlify dev

# Backend (once scaffolded)
cd backend && uv sync && uv run vital-server
cd backend && uv run pytest
cd backend && uv run ruff check app/
```

## Commit scopes

| Scope | Covers |
|-------|--------|
| `api` | Backend routes, endpoints |
| `config` | Configuration, env vars |
| `ios` | Swift iOS app |
| `docs` | Documentation (Mintlify) |

## Key constraints

- No medical diagnosis — always recommend a professional
- No secrets in code — everything via env vars
- Code and comments in English
- HealthKit is the health data source (not Thryve)
