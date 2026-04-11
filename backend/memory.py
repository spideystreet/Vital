"""Persistent memory store for V.I.T.A.L — one markdown file per user.

Sections: Baselines, Events, Protocols, Context, Challenges, Bookings. All
reads/writes happen through this module; no other file touches the markdown
directly.

Format:
    # <user_id>

    ## Baselines
    <entries...>

    ## Events
    <entries...>

    ## Protocols
    <entries...>

    ## Context
    <entries...>

    ## Challenges
    <entries...>

    ## Bookings
    <entries...>

Append-only. No locking — single-user hackathon scope.
"""

from __future__ import annotations

import re
from pathlib import Path
from statistics import mean, stdev

MEMORY_DIR = Path(__file__).resolve().parent.parent / "data" / "memory"

SECTION_BASELINES = "Baselines"
SECTION_EVENTS = "Events"
SECTION_PROTOCOLS = "Protocols"
SECTION_CONTEXT = "Context"
SECTION_CHALLENGES = "Challenges"
SECTION_BOOKINGS = "Bookings"

ALL_SECTIONS: list[str] = [
    SECTION_BASELINES,
    SECTION_EVENTS,
    SECTION_PROTOCOLS,
    SECTION_CONTEXT,
    SECTION_CHALLENGES,
    SECTION_BOOKINGS,
]


def _find_section_header(content: str, section: str) -> int:
    """Return the byte offset of the '## <section>' header line, or -1 if missing."""
    pattern = re.compile(rf"^## {re.escape(section)}$", re.MULTILINE)
    match = pattern.search(content)
    return match.start() if match else -1


def memory_path(user_id: str) -> Path:
    """Return the path to the memory file for a given user."""
    return MEMORY_DIR / f"{user_id}.md"


def ensure_memory_file(user_id: str) -> Path:
    """Create or migrate the memory file so every known section exists.

    - Missing file: write a fresh skeleton with all sections.
    - Existing file: append any sections added in later releases (idempotent).
    """
    path = memory_path(user_id)
    if not path.exists():
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        lines = [f"# {user_id}", ""]
        for section in ALL_SECTIONS:
            lines.append(f"## {section}")
            lines.append("")
        path.write_text("\n".join(lines))
        return path

    content = path.read_text()
    missing = [s for s in ALL_SECTIONS if _find_section_header(content, s) == -1]
    if missing:
        appended = content.rstrip() + "\n"
        for section in missing:
            appended += f"\n## {section}\n"
        path.write_text(appended)
    return path


def read_section(user_id: str, section: str) -> str:
    """Return the body of a section (everything between ## <section> and the next ##)."""
    if section not in ALL_SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {ALL_SECTIONS}")

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {section}"
    start = _find_section_header(content, section)
    if start == -1:
        return ""

    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)
    body_end = next_header if next_header != -1 else len(content)

    return content[body_start:body_end].strip()


def append_entry(user_id: str, section: str, entry: str) -> None:
    """Append a bullet line to a section. Entry is prefixed with '- '.

    Timestamps are the caller's responsibility (include them in `entry` if needed).
    """
    if section not in ALL_SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {ALL_SECTIONS}")

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {section}"
    start = content.find(marker)
    if start == -1:
        raise RuntimeError(
            f"Memory file for {user_id} is missing section {section}. "
            "File may be corrupted — delete and let ensure_memory_file recreate it."
        )

    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)

    new_line = f"- {entry}\n"

    if next_header == -1:
        new_content = content.rstrip() + "\n" + new_line
    else:
        insert_at = next_header + 1
        new_content = content[:insert_at] + new_line + content[insert_at:]

    path.write_text(new_content)


def read_all(user_id: str) -> str:
    """Return the full memory file as a string — suitable for LLM context injection."""
    return ensure_memory_file(user_id).read_text()


def format_baseline(metric: str, values: list[float], days: int) -> str:
    """Format a baseline one-liner for the Baselines section.

    Example: "hrv: mean=51.1 stddev=2.3 n=7 window=7d"
    """
    if not values:
        raise ValueError(f"Cannot compute baseline for {metric}: no values provided")

    m = round(mean(values), 1)
    sd = round(stdev(values), 1) if len(values) >= 2 else 0.0
    return f"{metric}: mean={m} stddev={sd} n={len(values)} window={days}d"


def upsert_baseline(
    user_id: str,
    metric: str,
    values: list[float],
    days: int,
) -> None:
    """Compute a baseline line for `metric` and replace any existing entry for it.

    Baselines are keyed by metric name (everything before the first ':'). A new
    call to upsert_baseline for the same metric overwrites the old line in place.
    """
    new_line = format_baseline(metric, values, days)

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {SECTION_BASELINES}"
    start = content.find(marker)
    if start == -1:
        raise RuntimeError(
            f"Memory file for {user_id} is missing section {SECTION_BASELINES}."
        )

    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)
    body_end = next_header if next_header != -1 else len(content)

    body = content[body_start:body_end]
    lines = body.split("\n")

    prefix = f"- {metric}:"
    kept = [line for line in lines if not line.startswith(prefix)]
    kept.append(f"- {new_line}")

    new_body = "\n" + "\n".join(line for line in kept if line.strip()) + "\n\n"

    path.write_text(content[:body_start] + new_body + content[body_end:])


# ---------------------------------------------------------------------------
# Challenges — personalized micro-goals created by the LLM
# ---------------------------------------------------------------------------

_CHALLENGE_LINE = re.compile(
    r'^\s*-\s*(\d{4}-\d{2}-\d{2}):\s*'
    r'title="([^"]+)"\s+'
    r'metric=(\w+)\s+'
    r'target=(\d+(?:\.\d+)?)\s+'
    r'status=(\w+)\s+'
    r'reason="([^"]+)"',
    re.MULTILINE,
)


def format_challenge(
    date_iso: str,
    title: str,
    metric: str,
    target: int | float,
    reason: str,
    status: str = "active",
) -> str:
    """Format a challenge entry for the Challenges section.

    Example:
        2026-04-11: title="Premiers pas" metric=steps target=500 status=active reason="..."
    """
    return (
        f'{date_iso}: title="{title}" metric={metric} target={target} '
        f'status={status} reason="{reason}"'
    )


def read_active_challenge(user_id: str) -> dict | None:
    """Return the most recent active challenge for the user, or None.

    Parses the Challenges section and returns the last entry whose
    status=active. Inactive/completed challenges are ignored.
    """
    body = read_section(user_id, SECTION_CHALLENGES)
    if not body:
        return None

    latest: dict | None = None
    for m in _CHALLENGE_LINE.finditer(body):
        if m.group(5) != "active":
            continue
        latest = {
            "date": m.group(1),
            "title": m.group(2),
            "metric": m.group(3),
            "target": float(m.group(4)),
            "status": m.group(5),
            "reason": m.group(6),
        }
    return latest


def read_all_challenges(user_id: str) -> list[dict]:
    """Return every challenge in the Challenges section, oldest first."""
    body = read_section(user_id, SECTION_CHALLENGES)
    if not body:
        return []
    return [
        {
            "date": m.group(1),
            "title": m.group(2),
            "metric": m.group(3),
            "target": float(m.group(4)),
            "status": m.group(5),
            "reason": m.group(6),
        }
        for m in _CHALLENGE_LINE.finditer(body)
    ]


# ---------------------------------------------------------------------------
# Bookings — specialist appointments confirmed via book_consultation tool
# ---------------------------------------------------------------------------

_BOOKING_LINE = re.compile(
    r'^\s*-\s*(\d{4}-\d{2}-\d{2}):\s*'
    r'specialty="([^"]+)"\s+'
    r'professional="([^"]+)"\s+'
    r'location="([^"]+)"\s+'
    r'slot="([^"]+)"\s+'
    r'urgency="([^"]+)"\s+'
    r'status="([^"]+)"\s+'
    r'reason="([^"]+)"',
    re.MULTILINE,
)


def format_booking(
    date_iso: str,
    specialty: str,
    professional: str,
    location: str,
    slot: str,
    urgency: str,
    reason: str,
    status: str = "confirmed",
) -> str:
    """Format a booking entry for the Bookings section.

    All fields are quoted so values containing spaces or punctuation survive
    a round-trip through the regex parser. Any double quotes inside values
    are flattened to single quotes to keep the format unambiguous.
    """

    def q(s: str) -> str:
        return str(s).replace('"', "'")

    return (
        f'{date_iso}: specialty="{q(specialty)}" '
        f'professional="{q(professional)}" '
        f'location="{q(location)}" '
        f'slot="{q(slot)}" '
        f'urgency="{q(urgency)}" '
        f'status="{q(status)}" '
        f'reason="{q(reason)}"'
    )


def read_bookings(user_id: str) -> list[dict]:
    """Return every booking in the Bookings section, oldest first."""
    body = read_section(user_id, SECTION_BOOKINGS)
    if not body:
        return []
    return [
        {
            "created_at": m.group(1),
            "specialty": m.group(2),
            "professional": m.group(3),
            "location": m.group(4),
            "slot": m.group(5),
            "urgency": m.group(6),
            "status": m.group(7),
            "reason": m.group(8),
        }
        for m in _BOOKING_LINE.finditer(body)
    ]
