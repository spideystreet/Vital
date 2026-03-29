"""V.I.T.A.L — Voice-Integrated Tracker & Adaptive Listener.

Main conversation loop orchestrating audio, LLM, and health data.
"""

import argparse
import sys

from mistralai.client import Mistral
from rich.console import Console
from rich.live import Live
from rich.text import Text

from vital.config import (
    DEMO_ASSISTANT_VOICE,
    DEMO_USER_VOICE,
    MISTRAL_API_KEY,
    ORANGE,
    ORANGE_DIM,
    REFRESH_FPS,
)
from vital.health_store import get_summary, init_db
from vital.viz import (
    SpeakingWaveform,
    ThinkingDots,
    animate_header,
    animate_vitals,
)

console = Console()

_SEP = f"  [{ORANGE_DIM}]─────────────────────────────────────[/]"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V.I.T.A.L health assistant")
    parser.add_argument("--text", action="store_true", help="Text-only mode (no microphone)")
    parser.add_argument("--no-speak", action="store_true", help="Disable TTS playback")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo mode: scripted conversation, both sides spoken via TTS",
    )
    return parser.parse_args()


def _get_query(text_mode: bool) -> str | None:
    """Get user input via voice or text."""
    if text_mode:
        try:
            console.print()
            return console.input(f"  [{ORANGE}]→[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

    # Voice mode
    from vital.audio import record
    from vital.voxtral import transcribe

    console.print()
    console.print(f"  [{ORANGE}]listening...[/]")
    try:
        audio_data = record()
        if not audio_data:
            console.print("  [dim]no speech detected[/dim]")
            return ""
        client = Mistral(api_key=MISTRAL_API_KEY)
        text = transcribe(client, audio_data)
        console.print(f"  [dim]→ {text}[/dim]")
        return text
    except Exception as e:
        console.print(f"  [red]audio error: {e}[/red]")
        return console.input(f"  [{ORANGE}]→[/] ").strip()


def _render_response(text: str, streaming: str = "", speaking: bool = False) -> Text | object:
    """Render the assistant response with optional waveform."""
    import shutil
    import textwrap

    from rich.console import Group

    parts = []
    label = Text()
    label.append("  vital 🎙", style=f"bold {ORANGE}")
    parts.append(label)
    parts.append(Text())
    content = streaming or text
    prefix = "  ▍ "
    width = shutil.get_terminal_size().columns
    wrapped_lines = textwrap.wrap(content, width=width - len(prefix) - 2) if content else [""]
    msg = Text()
    for i, line in enumerate(wrapped_lines):
        if i > 0:
            msg.append("\n")
        msg.append(prefix, style=f"{ORANGE}")
        msg.append(line)
    parts.append(msg)

    if speaking:
        parts.append(Text())
        parts.append(Text())
        parts.append(SpeakingWaveform())
        parts.append(Text())

    return Group(*parts)


def _show_thinking(duration: float = 0.8) -> None:
    """Show a brief thinking animation before the LLM responds."""
    import time as _time

    with Live(
        ThinkingDots(),
        refresh_per_second=8,
        vertical_overflow="visible",
        transient=True,
    ) as live:
        end = _time.monotonic() + duration
        while _time.monotonic() < end:
            live.update(ThinkingDots())
            _time.sleep(0.12)


def main():
    args = _parse_args()

    if not MISTRAL_API_KEY:
        console.print("[red]MISTRAL_API_KEY is not set.[/red]")
        sys.exit(1)

    import threading

    init_db()
    client = Mistral(api_key=MISTRAL_API_KEY)

    # Warm up TTS connection in background during startup animation
    def _warmup():
        import queue as _q

        from vital.voxtral import _stream_tts_to_queue

        q = _q.Queue()
        _stream_tts_to_queue(".", q, voice_id=DEMO_ASSISTANT_VOICE)

    warmup_t = threading.Thread(target=_warmup, daemon=True)
    warmup_t.start()

    # Animated header
    mode_label = "demo" if args.demo else ("text" if args.text else "voice")
    animate_header(console, mode_label)

    # Animated vitals
    summary = get_summary(24)
    if summary:
        animate_vitals(console, summary)

    # Wait for warmup to finish before starting conversation
    warmup_t.join()

    from vital.brain import build_system_message

    messages = [build_system_message()]

    if args.demo:
        _run_demo(client, messages)
    else:
        speak_mode = not args.text and not args.no_speak
        _run_loop(client, messages, text_mode=args.text, speak_mode=speak_mode)


# Scripted questions for the demo screencast
_DEMO_SCENARIO = [
    "Je me suis réveillé fatigué ce matin, t'as une idée de pourquoi ?",
]


def _run_demo(client: Mistral, messages: list[dict]) -> None:
    """Run a fully scripted demo — no input needed, both sides speak."""
    import time

    from vital.brain import build_system_message, stream_response
    from vital.voxtral import speak_streaming, speak_text

    for query in _DEMO_SCENARIO:
        time.sleep(2.0)

        # User question
        console.print()
        console.print()
        console.print("  [dim]you[/dim]")
        console.print()
        user_msg = Text()
        user_msg.append("  → ", style="bold white")
        user_msg.append(query)
        console.print(user_msg)
        console.print()

        speak_text(query, voice_id=DEMO_USER_VOICE)

        # Thinking
        messages.append({"role": "user", "content": query})
        messages[0] = build_system_message()

        _show_thinking(0.3)

        # Assistant response
        token_stream = stream_response(client, messages)
        full_text = ""

        with Live(
            _render_response("", speaking=True),
            refresh_per_second=REFRESH_FPS,
            vertical_overflow="visible",
        ) as live:
            for token in speak_streaming(client, token_stream, voice_id=DEMO_ASSISTANT_VOICE):
                full_text += token
                live.update(_render_response("", streaming=full_text, speaking=True))
            live.update(_render_response(full_text))

        messages.append({"role": "assistant", "content": full_text})

    console.print()
    console.print(_SEP)
    console.print()


def _run_loop(
    client: Mistral,
    messages: list[dict],
    text_mode: bool,
    speak_mode: bool,
) -> None:
    """Standard interactive conversation loop."""
    from vital.brain import build_system_message, stream_response

    while True:
        query = _get_query(text_mode)
        if query is None or query.lower() in ("quit", "exit", "q"):
            console.print()
            console.print(_SEP)
            console.print()
            break
        if not query:
            continue

        messages.append({"role": "user", "content": query})
        messages[0] = build_system_message()

        _show_thinking(0.6)

        token_stream = stream_response(client, messages)
        full_text = ""

        if speak_mode:
            from vital.voxtral import speak_streaming

            with Live(
                _render_response("", speaking=True),
                refresh_per_second=REFRESH_FPS,
                vertical_overflow="visible",
            ) as live:
                for token in speak_streaming(client, token_stream):
                    full_text += token
                    live.update(_render_response("", streaming=full_text, speaking=True))
                live.update(_render_response(full_text))
        else:
            with Live(
                _render_response(""),
                refresh_per_second=REFRESH_FPS,
                vertical_overflow="visible",
            ) as live:
                for token in token_stream:
                    full_text += token
                    live.update(_render_response("", streaming=full_text))
                live.update(_render_response(full_text))

        messages.append({"role": "assistant", "content": full_text})


if __name__ == "__main__":
    main()
