"""Voxtral STT and streaming TTS integration."""

import base64
import json
import queue
import re
import threading
from collections.abc import Iterator

import httpx
import numpy as np
import sounddevice as sd
from mistralai.client import Mistral

from vital.config import (
    AUDIO_OUTPUT_DEVICE,
    MISTRAL_API_KEY,
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
        language="fr",
    )
    return result.text.strip()


def speak_text(text: str, voice_id: str | None = None) -> None:
    """Speak a text string via TTS, streaming audio as chunks arrive."""
    q: queue.Queue[bytes | None] = queue.Queue()

    def _produce():
        _stream_tts_to_queue(text, q, voice_id=voice_id)
        q.put(None)

    t = threading.Thread(target=_produce, daemon=True)
    t.start()

    device = int(AUDIO_OUTPUT_DEVICE) if AUDIO_OUTPUT_DEVICE else None
    with sd.OutputStream(
        samplerate=TTS_SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=device,
    ) as stream:
        first = True
        while True:
            chunk = q.get()
            if chunk is None:
                break
            if first:
                silence = np.zeros(int(TTS_SAMPLE_RATE * 0.1), dtype=np.float32)
                stream.write(silence)
                first = False
            stream.write(np.frombuffer(chunk, dtype=np.float32))
    t.join()


# Shared audio level for reactive waveform (written by player, read by viz)
audio_level: float = 0.0


def speak_streaming(
    client: Mistral, token_stream: Iterator[str], voice_id: str | None = None
) -> Iterator[str]:
    """Stream TTS playback while yielding tokens for UI display.

    Buffers tokens into sentences, sends each to TTS in background threads,
    plays audio concurrently. Yields each token so caller can update the UI.
    """
    global audio_level  # noqa: PLW0603
    audio_q: queue.Queue[bytes | None] = queue.Queue()
    sentence_q: queue.Queue[str | None] = queue.Queue()

    def _player():
        global audio_level  # noqa: PLW0603
        device = int(AUDIO_OUTPUT_DEVICE) if AUDIO_OUTPUT_DEVICE else None
        with sd.OutputStream(
            samplerate=TTS_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=device,
        ) as stream:
            while True:
                data = audio_q.get()
                if data is None:
                    audio_level = 0.0
                    break
                samples = np.frombuffer(data, dtype=np.float32)
                rms = float(np.sqrt(np.mean(samples**2)))
                # Smooth: fast attack, slow decay
                audio_level = max(rms, audio_level * 0.85)
                stream.write(samples)

    def _tts_worker():
        while True:
            text = sentence_q.get()
            if text is None:
                break
            _stream_tts_to_queue(text, audio_q, voice_id=voice_id)
        audio_q.put(None)

    player_t = threading.Thread(target=_player, daemon=True)
    tts_t = threading.Thread(target=_tts_worker, daemon=True)
    player_t.start()
    tts_t.start()

    buffer = ""
    sentence_end = re.compile(r"[.!?:]\s")

    for token in token_stream:
        yield token
        buffer += token

        match = sentence_end.search(buffer)
        if match and len(buffer[: match.end()].strip()) >= 10:
            sentence = buffer[: match.end()].strip()
            buffer = buffer[match.end() :]
            sentence_q.put(sentence)

    if buffer.strip():
        sentence_q.put(buffer.strip())

    sentence_q.put(None)
    tts_t.join()
    player_t.join()


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
        body["voice"] = vid

    try:
        with httpx.stream("POST", url, headers=headers, json=body, timeout=30.0) as resp:
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
    except httpx.HTTPError:
        pass  # Graceful degradation — skip this sentence's audio
