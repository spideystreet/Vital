"""Voxtral STT and streaming TTS integration."""

import base64
import json
import logging
import queue
import re
import struct
import threading
from collections.abc import Iterator

import httpx
import numpy as np
from mistralai.client import Mistral

from backend.config import (
    MISTRAL_API_KEY,
    STT_LANGUAGE,
    STT_MODEL,
    TTS_MODEL,
    TTS_SAMPLE_RATE,
    TTS_VOICE_ID,
)


def transcribe(client: Mistral, audio_data: bytes) -> str:
    """Transcribe audio bytes to text using Voxtral."""
    result = client.audio.transcriptions.complete(
        model=STT_MODEL,
        file={"file_name": "recording.wav", "content": audio_data, "content_type": "audio/wav"},
        language=STT_LANGUAGE,
    )
    return result.text.strip()


_SENTENCE_END = re.compile(r"[.!?:]\s")


def _buffer_sentences(token_stream: Iterator[str], sentence_q: queue.Queue) -> Iterator[str]:
    """Yield tokens while buffering complete sentences into sentence_q for TTS."""
    buffer = ""
    for token in token_stream:
        yield token
        buffer += token
        match = _SENTENCE_END.search(buffer)
        if match and len(buffer[: match.end()].strip()) >= 10:
            sentence_q.put(buffer[: match.end()].strip())
            buffer = buffer[match.end() :]
    if buffer.strip():
        sentence_q.put(buffer.strip())
    sentence_q.put(None)


class _ForwardQueue:
    """Wraps a merged queue so _stream_tts_to_queue can push ('audio', bytes) events."""

    def __init__(self, merged: queue.Queue) -> None:
        self._merged = merged

    def put(self, chunk: bytes) -> None:
        if chunk is not None:
            self._merged.put(("audio", chunk))


def stream_voice_events(
    token_stream: Iterator[str], voice_id: str | None = None
) -> Iterator[tuple[str, bytes | str]]:
    """Yield ('text', token) and ('audio', pcm_bytes) events interleaved as they arrive.

    LLM tokens stream live to the caller AND are buffered into sentences that kick off
    Mistral TTS in a worker thread. Text and audio arrive in the merged stream in the
    order each backend produces them.
    """
    merged: queue.Queue = queue.Queue()
    sentence_q: queue.Queue[str | None] = queue.Queue()
    forward = _ForwardQueue(merged)

    def _tts_worker():
        try:
            while True:
                text = sentence_q.get()
                if text is None:
                    break
                _stream_tts_to_queue(text, forward, voice_id=voice_id)
        except Exception:
            logging.getLogger("backend.tts").exception("TTS worker crashed")
        finally:
            merged.put(("_audio_done", b""))

    def _producer():
        try:
            buffer = ""
            # Fire TTS on ANY clause boundary, not just sentence end.
            # This cuts 200-400ms of dead air on the first phrase.
            clause_end = re.compile(r"[,;:.!?]\s")
            first_chunk_sent = False
            for token in token_stream:
                merged.put(("text", token))
                buffer += token
                match = clause_end.search(buffer)
                if match:
                    chunk = buffer[: match.end()].strip()
                    # First chunk: fire as soon as we have ~4 chars (e.g., "Ok,").
                    # Subsequent chunks: wait for a more substantial clause (>=8 chars).
                    min_len = 4 if not first_chunk_sent else 8
                    if len(chunk) >= min_len:
                        buffer = buffer[match.end() :]
                        sentence_q.put(chunk)
                        first_chunk_sent = True
            if buffer.strip():
                sentence_q.put(buffer.strip())
        except Exception as exc:
            logging.getLogger("backend.llm").exception("LLM producer crashed")
            merged.put(("error", str(exc)))
        finally:
            sentence_q.put(None)  # Always signal TTS worker to stop
            merged.put(("_text_done", b""))

    tts_t = threading.Thread(target=_tts_worker, daemon=True)
    prod_t = threading.Thread(target=_producer, daemon=True)
    tts_t.start()
    prod_t.start()

    done_count = 0
    while done_count < 2:
        kind, payload = merged.get()
        if kind in ("_text_done", "_audio_done"):
            done_count += 1
            continue
        yield (kind, payload)  # "text", "audio", or "error"
    tts_t.join(timeout=5)
    prod_t.join(timeout=5)


def synthesize_wav_from_stream(
    token_stream: Iterator[str], voice_id: str | None = None
) -> tuple[bytes, str]:
    """Pipeline: LLM tokens -> sentence-based TTS -> concatenated WAV bytes.

    Starts TTS on each complete sentence while the LLM is still streaming.
    Returns the full WAV blob and the full assistant text.
    """
    audio_q: queue.Queue[bytes | None] = queue.Queue()
    sentence_q: queue.Queue[str | None] = queue.Queue()

    def _tts_worker():
        while True:
            text = sentence_q.get()
            if text is None:
                break
            _stream_tts_to_queue(text, audio_q, voice_id=voice_id)
        audio_q.put(None)

    tts_t = threading.Thread(target=_tts_worker, daemon=True)
    tts_t.start()

    full_text = ""
    for token in _buffer_sentences(token_stream, sentence_q):
        full_text += token

    chunks: list[np.ndarray] = []
    while True:
        data = audio_q.get()
        if data is None:
            break
        chunks.append(np.frombuffer(data, dtype=np.float32))
    tts_t.join()

    samples = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    return _pcm_to_wav(samples), full_text


def _pcm_to_wav(samples: np.ndarray) -> bytes:
    pcm16 = np.clip(samples, -1.0, 1.0)
    pcm16 = (pcm16 * 32767.0).astype("<i2").tobytes()
    num_channels = 1
    sample_width = 2
    byte_rate = TTS_SAMPLE_RATE * num_channels * sample_width
    block_align = num_channels * sample_width
    data_size = len(pcm16)
    fmt_chunk = struct.pack(
        "<4sIHHIIHH",
        b"fmt ",
        16,
        1,
        num_channels,
        TTS_SAMPLE_RATE,
        byte_rate,
        block_align,
        sample_width * 8,
    )
    data_chunk = struct.pack("<4sI", b"data", data_size) + pcm16
    riff = b"RIFF" + struct.pack("<I", 4 + len(fmt_chunk) + len(data_chunk)) + b"WAVE"
    return riff + fmt_chunk + data_chunk


def synthesize_wav(text: str, voice_id: str | None = None) -> bytes:
    """Synthesize text to a complete WAV byte blob (16-bit PCM mono, TTS_SAMPLE_RATE)."""
    q: queue.Queue[bytes | None] = queue.Queue()
    _stream_tts_to_queue(text, q, voice_id=voice_id)
    q.put(None)

    chunks: list[np.ndarray] = []
    while True:
        data = q.get()
        if data is None:
            break
        chunks.append(np.frombuffer(data, dtype=np.float32))

    samples = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    return _pcm_to_wav(samples)


# Shared HTTP client with keep-alive pool — saves ~80-150ms TLS RTT per sentence
_tts_http_client: httpx.Client | None = None
_tts_http_lock = threading.Lock()


def _get_tts_client() -> httpx.Client:
    global _tts_http_client  # noqa: PLW0603
    with _tts_http_lock:
        if _tts_http_client is None:
            _tts_http_client = httpx.Client(
                http2=False,
                timeout=30.0,
                limits=httpx.Limits(
                    max_keepalive_connections=4,
                    max_connections=8,
                    keepalive_expiry=60.0,
                ),
            )
        return _tts_http_client


def prewarm_tts() -> None:
    """Open the TLS connection to the TTS endpoint ahead of the first request.
    Called at turn start so the first sentence doesn't pay the handshake cost.
    """
    try:
        client = _get_tts_client()
        client.head("https://api.mistral.ai/v1/audio/speech", timeout=2.0)
    except httpx.HTTPError:
        pass


def _stream_tts_to_queue(text: str, audio_q: queue.Queue, voice_id: str | None = None) -> None:
    """Stream TTS audio via HTTP/SSE and push PCM chunks to queue."""
    url = "https://api.mistral.ai/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "model": TTS_MODEL,
        "input": text,
        "response_format": "pcm",
        "stream": True,
    }
    vid = voice_id or TTS_VOICE_ID
    if vid:
        body["voice_id"] = vid

    try:
        client = _get_tts_client()
        with client.stream("POST", url, headers=headers, json=body) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                audio_b64 = event.get("audio_data") or event.get("data", "")
                if audio_b64:
                    audio_q.put(base64.b64decode(audio_b64))
    except httpx.HTTPError as exc:
        logging.getLogger("backend.tts").warning("TTS failed for chunk: %s", exc)
