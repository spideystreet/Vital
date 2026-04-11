# Skill: Audit Python

## Checklist

### Error handling at system boundaries
- [ ] Thryve API calls (`thryve.py`) — what happens if Thryve QA is unreachable or returns 5xx?
- [ ] Memory file I/O (`memory.py`) — what happens if the memory file is missing or unwritable?
- [ ] Mistral API calls (`brain.py`, `coach.py`, `voxtral.py`) — what happens if the API is unreachable or returns an error?
- [ ] Tool execution (`execute_tool`) — what happens if a tool raises an exception?
- [ ] FastAPI endpoints — are HTTP errors returned with proper status codes?

### Data integrity
- [ ] Memory sections (`Baselines`, `Events`, `Protocols`, `Context`) are parsed correctly and tolerate missing sections
- [ ] Baseline math (`upsert_baseline`, z-score in `nudge.py`) handles empty/short series without division by zero
- [ ] `get_trend()`, `get_correlation()`, `compare_periods()` handle empty Thryve results
- [ ] Dashboard delta math (`_compute_delta_pct`) returns 0.0 when no baseline exists (no NaN, no crash)

### Code quality
- [ ] No unused imports
- [ ] No hardcoded secrets (API keys, passwords, DB names)
- [ ] Consistent naming (snake_case functions/vars)
- [ ] No dead code or commented-out blocks
- [ ] Docstrings on public functions

### LLM tool use
- [ ] All 9 tools defined in `TOOLS` list match `execute_tool()` dispatch (`brain.py`)
- [ ] `read_memory` / `append_memory` round-trip through `memory.py` (not direct file I/O)
- [ ] Tool descriptions are clear enough for the LLM to choose correctly
- [ ] Tool parameter types match what the functions expect
- [ ] `book_consultation` is clearly simulated (not real booking)

### Security
- [ ] `.env` is in `.gitignore`
- [ ] No secrets in code, config files, or seed data
- [ ] No PII in system prompt or health context sent to Mistral

## Output format

Report findings as:
```
file.py:line — [severity] description
```
Severity: CRITICAL / WARNING / INFO

Do NOT modify files unless explicitly asked. This is a read-only audit by default.
