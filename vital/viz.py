"""Terminal visualizations — Mistral pixel aesthetic."""

import math
import time

from rich.console import Console
from rich.text import Text

from vital.config import ORANGE, ORANGE_DARK, ORANGE_DIM

BLOCK_CHARS = " ▁▂▃▄▅▆▇█"

_HEADER_LINES = [
    "  ██╗   ██╗ ██╗ ████████╗  █████╗  ██╗",
    "  ██║   ██║ ██║ ╚══██╔══╝ ██╔══██╗ ██║",
    "  ██║   ██║ ██║    ██║    ███████║ ██║",
    "  ╚██╗ ██╔╝ ██║    ██║    ██╔══██║ ██║",
    "   ╚████╔╝  ██║    ██║    ██║  ██║ ███████╗",
    "    ╚═══╝   ╚═╝    ╚═╝    ╚═╝  ╚═╝ ╚══════╝",
]

# Gradient from bright to dim orange, top to bottom
_HEADER_STYLES = [
    f"bold {ORANGE}",
    f"bold {ORANGE}",
    ORANGE,
    ORANGE,
    ORANGE_DIM,
    ORANGE_DARK,
]


def animate_header(console: Console, mode: str) -> None:
    """Reveal the VITAL header line by line with gradient."""
    console.print()
    for line, style in zip(_HEADER_LINES, _HEADER_STYLES):
        console.print(f"[{style}]{line}[/]")
        time.sleep(0.06)
    console.print()
    console.print(f"  [dim]{mode} mode[/dim]")


def animate_vitals(console: Console, summary: dict) -> None:
    """Reveal health metrics one by one with a scan effect."""
    if not summary:
        return

    console.print()
    console.print(f"  [{ORANGE_DIM}]─────────────────────────────────────[/]")
    console.print()

    for metric, stats in summary.items():
        unit = stats.get("unit") or ""
        line = Text()
        line.append(f"  {metric:<20s}", style=f"bold {ORANGE}")
        line.append(f"{stats['latest']:>8} {unit:<5s}", style="white")
        line.append(f"  {stats['min']}–{stats['max']}", style="dim")
        console.print(line)
        time.sleep(0.08)

    console.print()
    console.print(f"  [{ORANGE_DIM}]─────────────────────────────────────[/]")


def render_listening(level: float) -> Text:
    """Render an animated waveform reactive to microphone input level."""
    t = time.monotonic()
    intensity = min(level / 300, 1.0)
    half = 15

    bars: list[float] = []
    for i in range(half):
        wave = math.sin(t * 6 + i * 0.7) * 0.35 + math.sin(t * 9 + i * 0.4) * 0.25 + 0.25
        envelope = 1.0 - (i / half) * 0.5
        height = wave * envelope * (0.2 + intensity * 0.8)
        bars.append(max(0.05, min(height, 1.0)))

    bars = list(reversed(bars)) + bars

    text = Text()
    text.append("  ", style="bold")
    for b in bars:
        idx = int(b * (len(BLOCK_CHARS) - 1))
        char = BLOCK_CHARS[idx]
        if b > 0.6:
            style = f"bold {ORANGE}"
        elif b > 0.3:
            style = ORANGE_DIM
        else:
            style = ORANGE_DARK
        text.append(char, style=style)
    return text


class SpeakingWaveform:
    """Rich renderable for audio-reactive waveform."""

    def __rich_console__(self, console, options):
        from vital.voxtral import audio_level

        t = time.monotonic()
        width = min(options.max_width - 4, 60)
        half = width // 2

        # audio_level is RMS (typically 0.0–0.15 for voice), boost to 0.0–1.0
        intensity = min(audio_level * 12.0, 1.0)
        # Visible animation even when silent, full bars when loud
        base = 0.08 + intensity * 0.7

        bars: list[float] = []
        for i in range(half):
            wave = (
                math.sin(t * 5.0 + i * 0.5) * 0.3
                + math.sin(t * 8.0 + i * 0.35) * 0.2
                + math.sin(t * 12 + i * 0.2) * 0.1
            )
            envelope = 1.0 - (i / half) * 0.25
            height = (base + wave * intensity) * envelope
            bars.append(max(0.02, min(height, 1.0)))

        bars = list(reversed(bars)) + bars

        text = Text()
        text.append("  ", style="bold")
        for b in bars:
            idx = int(b * (len(BLOCK_CHARS) - 1))
            char = BLOCK_CHARS[idx]
            if b > 0.7:
                style = f"bold {ORANGE}"
            elif b > 0.5:
                style = ORANGE
            elif b > 0.3:
                style = ORANGE_DIM
            else:
                style = ORANGE_DARK
            text.append(char, style=style)
        yield text


class ThinkingDots:
    """Animated thinking indicator."""

    def __rich_console__(self, console, options):
        t = time.monotonic()
        n = int(t * 3) % 4
        dots = "·" * n + " " * (3 - n)
        text = Text()
        text.append(f"  ▍ {dots}", style=f"{ORANGE_DIM}")
        yield text


def render_health_banner(summary: dict) -> Text:
    """Render a minimal health data banner for the terminal."""
    text = Text()
    for metric, stats in summary.items():
        unit = stats.get("unit") or ""
        text.append(f"  {metric:<20s}", style=f"bold {ORANGE}")
        text.append(f"{stats['latest']:>8} {unit:<5s}", style="white")
        text.append(f"  {stats['min']}–{stats['max']}\n", style="dim")
    return text
