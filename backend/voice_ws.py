"""Realtime voice WebSocket endpoint.

Pipeline per turn:
1. iPhone opens a WS and streams raw PCM16 LE @ 16 kHz as binary frames.
2. Backend forwards bytes to Mistral realtime STT (voxtral-mini-transcribe-realtime-2602).
3. Partial transcripts are pushed to the iPhone live (text JSON).
4. On `transcription.done`: kick off LLM (mistral-small-latest) + streaming TTS.
5. LLM tokens (text JSON) and TTS PCM (binary) are streamed back to the iPhone.
6. Loop: same WS stays open for the next turn.
"""

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from mistralai.client import Mistral
from mistralai.client.models import AudioFormat

from backend.brain import PatientContext, SessionData, build_system_message, stream_response
from backend.config import DEMO_ASSISTANT_VOICE, MISTRAL_API_KEY, REALTIME_STT_MODEL
from backend.voxtral import prewarm_tts, stream_voice_events

logger = logging.getLogger("backend.ws")

STREAMING_DELAY_MS = 240  # "fast" profile from Mistral docs


async def _send_text(ws: WebSocket, obj: dict[str, Any]) -> None:
    try:
        await ws.send_text(json.dumps(obj, ensure_ascii=False))
    except RuntimeError:
        pass  # WS already closed — safe to ignore


async def _run_turn(
    ws: WebSocket, user_text: str, loop: asyncio.AbstractEventLoop,
    system_msg: dict, client: Mistral,
) -> None:
    """Run LLM + TTS for one finalized user utterance."""
    t0 = time.monotonic()
    await _send_text(ws, {"type": "state", "value": "thinking"})

    messages = [system_msg, {"role": "user", "content": user_text}]
    events_q: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue()

    def _produce():
        last_err = None
        for attempt in range(3):
            try:
                token_stream = stream_response(client, messages)
                for kind, payload in stream_voice_events(
                    token_stream, voice_id=DEMO_ASSISTANT_VOICE
                ):
                    asyncio.run_coroutine_threadsafe(
                        events_q.put((kind, payload)), loop
                    )
                last_err = None
                break  # success
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                is_transient = "503" in str(exc) or "timeout" in str(exc).lower()
                if is_transient and attempt < 2:
                    logger.warning("LLM attempt %d failed (503), retrying...", attempt + 1)
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break
        if last_err is not None:
            logger.exception("LLM/TTS pipeline failed after retries")
            asyncio.run_coroutine_threadsafe(
                events_q.put(("error", str(last_err))), loop
            )
        asyncio.run_coroutine_threadsafe(events_q.put(None), loop)

    import threading
    threading.Thread(target=_produce, daemon=True).start()

    first_text = False
    speaking_announced = False
    while True:
        item = await events_q.get()
        if item is None:
            break
        kind, payload = item
        if kind == "text":
            if not first_text:
                first_text = True
                dt = int((time.monotonic() - t0) * 1000)
                logger.info("LLM TTFT: %dms", dt)
                await _send_text(ws, {"type": "state", "value": "responding", "elapsed_ms": dt})
            await _send_text(ws, {"type": "token", "text": payload})
        elif kind == "audio":
            if not speaking_announced:
                dt = int((time.monotonic() - t0) * 1000)
                logger.info("TTS first audio: %dms (LLM→TTS delta: %dms)", dt, dt)
                await _send_text(ws, {"type": "state", "value": "speaking", "elapsed_ms": dt})
                speaking_announced = True
            await ws.send_bytes(payload)
        elif kind == "error":
            await _send_text(ws, {"type": "error", "message": payload})

    dt_total = int((time.monotonic() - t0) * 1000)
    logger.info("Turn complete: %dms total", dt_total)
    await _send_text(ws, {"type": "state", "value": "listening"})


async def handle_voice_ws(ws: WebSocket) -> None:
    await ws.accept()
    loop = asyncio.get_running_loop()

    # Reuse a single Mistral client for the entire WS session (keeps HTTP pool warm)
    client = Mistral(api_key=MISTRAL_API_KEY)

    # Pre-build system message once at connection time (avoid DB hit per turn)
    _ws_patient = PatientContext(token="", name="user")
    _ws_session = SessionData()
    system_msg = await loop.run_in_executor(
        None, lambda: build_system_message(_ws_patient, _ws_session)
    )

    # Pre-warm TTS TLS connection once at session start (keepalive_expiry=60s keeps it warm)
    loop.run_in_executor(None, prewarm_tts)

    # Client→server binary PCM chunks land here; the realtime STT reads from this queue.
    audio_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=128)

    async def _audio_iter():
        """Single async iterator consumed by one transcribe_stream session."""
        while True:
            chunk = await audio_q.get()
            if chunk is None:
                return
            yield chunk

    stt_task: asyncio.Task | None = None
    stop_event = asyncio.Event()

    async def _run_one_session():
        """One STT session — ends after a single transcription.done."""
        audio_format = AudioFormat(
            encoding="pcm_s16le",
            sample_rate=16000,
        )
        stream = client.audio.realtime.transcribe_stream(
            audio_stream=_audio_iter(),
            model=REALTIME_STT_MODEL,
            audio_format=audio_format,
            target_streaming_delay_ms=STREAMING_DELAY_MS,
        )
        partial_buf = ""
        async for event in stream:
            etype = type(event).__name__
            if etype == "TranscriptionStreamTextDelta":
                partial_buf += event.text
                await _send_text(ws, {"type": "partial", "text": partial_buf})
            elif etype == "TranscriptionStreamDone":
                return (getattr(event, "text", "") or partial_buf).strip()
            elif etype == "RealtimeTranscriptionError":
                await _send_text(
                    ws,
                    {"type": "error", "message": str(getattr(event, "error", event))},
                )
                return ""
        return partial_buf.strip()

    async def _stt_loop():
        """Outer loop — spins up a new STT session after every turn."""
        try:
            while not stop_event.is_set():
                await _send_text(ws, {"type": "state", "value": "listening"})
                stt_t0 = time.monotonic()
                final_text = await _run_one_session()
                if not final_text:
                    continue
                stt_ms = int((time.monotonic() - stt_t0) * 1000)
                logger.info("STT done in %dms — User said: %s", stt_ms, final_text)
                await _send_text(ws, {"type": "final", "text": final_text})
                # Drain any stale audio accumulated during the previous session
                while not audio_q.empty():
                    try:
                        audio_q.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                await _run_turn(ws, final_text, loop, system_msg, client)
        except Exception as exc:  # noqa: BLE001
            logger.exception("STT loop failed")
            try:
                await _send_text(ws, {"type": "error", "message": str(exc)})
            except Exception:  # noqa: BLE001
                pass
        finally:
            stop_event.set()

    stt_task = asyncio.create_task(_stt_loop())

    try:
        while not stop_event.is_set():
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if (data := msg.get("bytes")) is not None:
                try:
                    audio_q.put_nowait(data)
                except asyncio.QueueFull:
                    # Drop oldest chunk to keep audio fresh
                    try:
                        audio_q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        audio_q.put_nowait(data)
                    except asyncio.QueueFull:
                        pass
            elif (text := msg.get("text")) is not None:
                try:
                    ctrl = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if ctrl.get("type") == "end":
                    break
                elif ctrl.get("type") == "end_speech":
                    # Client VAD detected silence — end the current audio stream
                    # so STT emits transcription.done and the turn can fire
                    logger.info("Client signaled end_speech")
                    await audio_q.put(None)
    except WebSocketDisconnect:
        pass
    finally:
        await audio_q.put(None)
        if stt_task is not None:
            stt_task.cancel()
            try:
                await stt_task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
