"""Persistent memory store for V.I.T.A.L — one markdown file per user.

Sections: Baselines, Events, Protocols, Context. All reads/writes happen
through this module; no other file touches the markdown directly.

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

Append-only. No locking — single-user hackathon scope.
"""

from __future__ import annotations

from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent / "data" / "memory"

SECTION_BASELINES = "Baselines"
SECTION_EVENTS = "Events"
SECTION_PROTOCOLS = "Protocols"
SECTION_CONTEXT = "Context"

ALL_SECTIONS: list[str] = [
    SECTION_BASELINES,
    SECTION_EVENTS,
    SECTION_PROTOCOLS,
    SECTION_CONTEXT,
]


def memory_path(user_id: str) -> Path:
    """Return the path to the memory file for a given user."""
    return MEMORY_DIR / f"{user_id}.md"


def ensure_memory_file(user_id: str) -> Path:
    """Create the memory file with an empty section skeleton if missing.

    Idempotent: existing files are not touched.
    """
    path = memory_path(user_id)
    if path.exists():
        return path

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"# {user_id}", ""]
    for section in ALL_SECTIONS:
        lines.append(f"## {section}")
        lines.append("")
    path.write_text("\n".join(lines))
    return path


def read_section(user_id: str, section: str) -> str:
    """Return the body of a section (everything between ## <section> and the next ##)."""
    if section not in ALL_SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {ALL_SECTIONS}")

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {section}"
    start = content.find(marker)
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
