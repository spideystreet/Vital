# Vital

> Finally, your health data works for you.

Core mobile repo — iOS (SwiftUI) app lives here.  
AI, analytics, and internal specs are separate repos.

## Project structure

```
mobile/
  ios/             # SwiftUI iOS app (primary)
  android/         # Android app
docs/              # Mintlify product landing site
public/            # Static assets (badges, mockups, model logos)
```

## Related repos (siblings under `Vital Vie` organization)

| Repo | Purpose |
|------|---------|
| `vital-conscience` | Python FastAPI backend (AI powered) |
| `vital-analytics` | Swift Package — on-device HealthKit analytics consumed by `mobile/ios` |
| `vital-docs` | Internal specs / private notes |

## Commands

```bash
# iOS — open in Xcode
open mobile/ios/*.xcodeproj   # or *.xcworkspace
```

## Commit scopes

| Scope | Covers |
|-------|--------|
| `ios` | Swift iOS app (`mobile/ios/`) |
| `android` | Android app (`mobile/android/`) |
| `docs` | Mintlify landing (`docs/`) |

## Key constraints

- No medical diagnosis — always recommend a professional
- No secrets in code — everything via env vars
- Code and comments in English
- HealthKit is the iOS health data source
