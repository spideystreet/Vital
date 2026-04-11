"""V.I.T.A.L Health Server — FastAPI backend with SSE streaming for web frontend.

Endpoints:
    POST /api/checkup/start      → start a new checkup session
    POST /api/checkup/audio      → transcribe audio (STT)
    POST /api/checkup/respond    → SSE stream (emotion, health_data, text, etc.)
    GET  /api/patients           → list hardcoded patients
    GET  /api/patient/{id}/summary → patient burnout summary
    GET  /api/nudge/{patient_id} → biometric nudge check

Legacy (kept):
    POST /health                 → HealthKit data ingestion
    GET  /health/ping            → liveness check
    WS   /voice/ws               → realtime voice WebSocket
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from mistralai.client import Mistral
from pydantic import BaseModel
from uvicorn import run as uvicorn_run

from backend.brain import (
    PatientContext,
    SessionData,
    build_system_message,
    chat_with_tools,
)
from backend.burnout import BurnoutResult, compute_burnout
from backend.config import (
    DEMO_ASSISTANT_VOICE,
    HEALTH_SERVER_HOST,
    HEALTH_SERVER_PORT,
    MISTRAL_API_KEY,
    require_thryve_credentials,
)
from backend.guardrail import check_response
from backend.health_store import init_db, insert_metrics
from backend.thryve import ThryveClient
from backend.voice_ws import handle_voice_ws
from backend.voxtral import prewarm_tts, stream_voice_events, transcribe

logger = logging.getLogger("backend.server")

# ---------------------------------------------------------------------------
# Patient registry (hardcoded for hackathon demo)
# ---------------------------------------------------------------------------

# Pre-made Thryve data profile — see docs/thryve-hackathon-guide.md
# Default: "Active Gym Guy" (Whoop) — rich HRV data fits the demo narrative.
# Override via env var if a different profile is chosen at demo time.
_DEMO_THRYVE_END_USER_ID = os.environ.get(
    "VITAL_DEMO_THRYVE_TOKEN",
    "2bfaa7e6f9455ceafa0a59fd5b80496c",
)

PATIENTS = [
    {
        "id": "patient-1",
        "name": "Sophie Martin",  # Persona name — the Thryve profile is anonymous
        "age": 34,
        "token": _DEMO_THRYVE_END_USER_ID,
    },
]

_PATIENTS_BY_ID: dict[str, dict] = {p["id"]: p for p in PATIENTS}

# ---------------------------------------------------------------------------
# Notification broadcast — in-process pub/sub for Surface 3
# ---------------------------------------------------------------------------

_notification_subscribers: set[asyncio.Queue] = set()


async def _broadcast_notification(payload: dict) -> None:
    """Push a notification payload to every subscribed SSE stream."""
    dead: list[asyncio.Queue] = []
    for queue in _notification_subscribers:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(queue)
    for q in dead:
        _notification_subscribers.discard(q)


# ---------------------------------------------------------------------------
# Session management (in-memory)
# ---------------------------------------------------------------------------


@dataclass
class SessionState:
    session_id: str
    patient_id: str
    patient_ctx: PatientContext
    session_data: SessionData
    messages: list[dict] = field(default_factory=list)
    user_transcript: str = ""
    turn_count: int = 0


sessions: dict[str, SessionState] = {}

# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def sse_event(event: str, data: dict) -> str:
    """Format a single SSE event line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Mistral client singleton
# ---------------------------------------------------------------------------

_mistral_client: Mistral | None = None


def _get_mistral() -> Mistral:
    global _mistral_client  # noqa: PLW0603
    if _mistral_client is None:
        _mistral_client = Mistral(api_key=MISTRAL_API_KEY)
    return _mistral_client


# Thryve client singleton
_thryve_client: ThryveClient | None = None


def _get_thryve() -> ThryveClient:
    global _thryve_client  # noqa: PLW0603
    if _thryve_client is None:
        _thryve_client = ThryveClient()
    return _thryve_client


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    require_thryve_credentials()
    init_db()
    logger.info("Database initialized")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="V.I.T.A.L Health Server", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartCheckupRequest(BaseModel):
    patient_id: str


class StartCheckupResponse(BaseModel):
    session_id: str


class RespondRequest(BaseModel):
    session_id: str
    transcript: str


class HealthPayload(BaseModel):
    metrics: list[dict]


# ---------------------------------------------------------------------------
# New API endpoints
# ---------------------------------------------------------------------------


@app.post("/api/checkup/start", response_model=StartCheckupResponse)
async def start_checkup(req: StartCheckupRequest):
    """Start a new checkup session for a patient."""
    if req.patient_id not in _PATIENTS_BY_ID:
        raise HTTPException(status_code=404, detail="Patient not found")

    session_id = str(uuid.uuid4())
    patient = _PATIENTS_BY_ID[req.patient_id]

    # Build initial system message with patient context
    patient_ctx = PatientContext(
        token=patient.get("token", ""),
        name=patient["name"],
        age=patient.get("age"),
    )
    session_data = SessionData()
    system_msg = build_system_message(patient_ctx, session_data)

    session = SessionState(
        session_id=session_id,
        patient_id=req.patient_id,
        patient_ctx=patient_ctx,
        session_data=session_data,
        messages=[system_msg],
    )
    sessions[session_id] = session
    logger.info("Session %s started for patient %s", session_id, req.patient_id)
    return StartCheckupResponse(session_id=session_id)


@app.post("/api/checkup/audio")
async def checkup_audio(audio: UploadFile = File(...)):
    """Transcribe uploaded audio to text via Voxtral STT."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio")

    # Pre-warm TTS while STT runs
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, prewarm_tts)

    client = _get_mistral()
    try:
        user_text = await loop.run_in_executor(None, transcribe, client, audio_bytes)
    except Exception as exc:
        logger.exception("STT failed")
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc

    if not user_text:
        user_text = "(silence)"

    logger.info("Transcribed: %s", user_text)
    return {"transcript": user_text}


@app.post("/api/checkup/respond")
async def checkup_respond(req: RespondRequest):
    """Process a user transcript and return SSE stream with full checkup flow.

    Event types: emotion, health_data, text, audio, burnout_score, protocol, done.
    """
    session = sessions.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    patient = _PATIENTS_BY_ID[session.patient_id]
    session.user_transcript = req.transcript
    session.turn_count += 1

    # Add user message to conversation history
    session.messages.append({"role": "user", "content": req.transcript})

    async def event_stream():
        loop = asyncio.get_running_loop()
        client = _get_mistral()
        thryve = _get_thryve()
        user_token = patient.get("token", "")

        # Step a: thinking
        yield sse_event("emotion", {"state": "thinking", "label": "Je réfléchis..."})

        # Step b: fetch health data from Thryve and emit health_data events
        yield sse_event("emotion", {"state": "curious", "label": "Je regarde tes données..."})

        burnout_result: BurnoutResult | None = None
        try:
            if user_token:
                burnout_metrics = await thryve.get_burnout_metrics(user_token)

                # Emit health_data events for each metric
                for metric_name, metric_data in burnout_metrics.items():
                    if metric_data.get("latest") is not None:
                        trend = "stable"
                        if metric_data.get("baseline_7d") and metric_data["latest"]:
                            baseline = metric_data["baseline_7d"]
                            current = metric_data["latest"]
                            pct = ((current - baseline) / baseline) * 100 if baseline else 0
                            if pct > 5:
                                trend = "up"
                            elif pct < -5:
                                trend = "down"
                        yield sse_event("health_data", {
                            "metric": metric_name,
                            "value": metric_data["latest"],
                            "trend": trend,
                        })

                # Compute burnout score from Thryve analytics
                burnout_result = await loop.run_in_executor(
                    None, compute_burnout, burnout_metrics,
                )
        except Exception:
            logger.exception("Thryve data fetch failed, continuing without health data")

        # Step c: LLM with tool use
        messages_copy = list(session.messages)

        tool_results: list[dict] = []
        try:
            llm_text, _emotions, tool_results = await loop.run_in_executor(
                None,
                lambda: chat_with_tools(
                    client, messages_copy, session.patient_ctx, session.session_data,
                ),
            )
            llm_response = llm_text
        except Exception:
            logger.exception("LLM call failed")
            llm_response = "Désolé, je n'arrive pas à me connecter. Réessaie dans un instant."

        # Step d: guardrail check
        try:
            guard_result = await check_response(req.transcript, llm_response)
            final_text = guard_result.safe_response
            if not guard_result.safe:
                yield sse_event("emotion", {"state": "concerned", "label": "Reformulation..."})
        except Exception:
            logger.exception("Guardrail check failed, using raw response")
            final_text = llm_response

        # Update session history with assistant response
        session.messages.append({"role": "assistant", "content": final_text})

        # Step e: surface tool side-effects to the frontend (booking popup, challenge badge)
        booking_record = next(
            (tr for tr in tool_results if tr["name"] == "book_consultation"),
            None,
        )
        challenge_record = next(
            (tr for tr in tool_results if tr["name"] == "propose_challenge"),
            None,
        )

        if booking_record:
            yield sse_event("booking", booking_record["result"])
        if challenge_record:
            yield sse_event("challenge", challenge_record["result"])

        # Emotion reflects the actual conversation flow: tool calls first,
        # then burnout score as a fallback when no side-effect fired.
        tool_names = {tr["name"] for tr in tool_results}
        if booking_record:
            yield sse_event(
                "emotion",
                {"state": "encouraging", "label": "Je te réserve ça"},
            )
        elif challenge_record:
            yield sse_event(
                "emotion",
                {"state": "encouraging", "label": "Nouveau défi pour toi"},
            )
        elif "read_memory" in tool_names or "append_memory" in tool_names:
            yield sse_event(
                "emotion",
                {"state": "thinking", "label": "Je me rappelle"},
            )
        elif burnout_result and burnout_result.score >= 60:
            yield sse_event(
                "emotion",
                {"state": "alert", "label": "Attention, score élevé"},
            )
        elif burnout_result and burnout_result.score >= 30:
            yield sse_event(
                "emotion",
                {"state": "concerned", "label": "Je détecte du stress"},
            )
        else:
            yield sse_event(
                "emotion",
                {"state": "encouraging", "label": "Bonne nouvelle !"},
            )

        # Send text in small chunks (simulate streaming feel)
        words = final_text.split(" ")
        chunk = ""
        for word in words:
            chunk += word + " "
            if len(chunk) >= 15:
                yield sse_event("text", {"chunk": chunk})
                chunk = ""
                await asyncio.sleep(0.02)
        if chunk.strip():
            yield sse_event("text", {"chunk": chunk})

        # Step f: stream audio (TTS)
        try:
            def _generate_audio():
                """Generate TTS audio chunks from final text."""
                # Use stream_voice_events with a single-item text iterator
                def _text_iter():
                    yield final_text
                for kind, payload in stream_voice_events(
                    _text_iter(), voice_id=DEMO_ASSISTANT_VOICE
                ):
                    if kind == "audio":
                        yield payload

            audio_chunks = await loop.run_in_executor(None, lambda: list(_generate_audio()))
            for chunk_bytes in audio_chunks:
                b64 = base64.b64encode(chunk_bytes).decode("ascii")
                yield sse_event("audio", {"base64_pcm_chunk": b64})
        except Exception:
            logger.exception("TTS streaming failed")

        # Step g: burnout score
        if burnout_result:
            yield sse_event("burnout_score", {
                "score": burnout_result.score,
                "level": burnout_result.level,
            })

        # Step h: protocol (3 actions)
        protocol_actions = _extract_protocol(final_text, burnout_result)
        yield sse_event("protocol", {"actions": protocol_actions})

        # Step i: done
        yield sse_event("done", {})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/patients")
async def list_patients():
    """Return the list of demo patients."""
    return [
        {"id": p["id"], "name": p["name"], "token": p["token"]}
        for p in PATIENTS
    ]


@app.get("/api/patient/{patient_id}/summary")
async def patient_summary(patient_id: str):
    """Return a patient's burnout summary."""
    patient = _PATIENTS_BY_ID.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    loop = asyncio.get_running_loop()
    thryve = _get_thryve()
    user_token = patient.get("token", "")

    burnout_result: BurnoutResult | None = None
    try:
        if user_token:
            metrics = await thryve.get_burnout_metrics(user_token)
            burnout_result = await loop.run_in_executor(
                None, compute_burnout, metrics,
            )
    except Exception:
        logger.exception("Failed to fetch burnout metrics for %s", patient_id)

    return {
        "burnout_score": burnout_result.score if burnout_result else None,
        "level": burnout_result.level if burnout_result else None,
        "protocol": _extract_protocol(None, burnout_result),
        "last_checkup": None,  # TODO: track from sessions
    }


@app.get("/api/nudge/{patient_id}")
async def nudge_check(patient_id: str):
    """Check if a biometric nudge should be triggered for the patient."""
    if patient_id not in _PATIENTS_BY_ID:
        raise HTTPException(status_code=404, detail="Patient not found")

    from backend.nudge import evaluate

    loop = asyncio.get_running_loop()
    try:
        decision = await loop.run_in_executor(None, evaluate)
        return {
            "triggered": decision.should_nudge,
            "message": decision.headline,
            "signals": decision.reasons,
        }
    except Exception:
        logger.exception("Nudge evaluation failed")
        return {"triggered": False, "message": None, "signals": []}


# ---------------------------------------------------------------------------
# Coach endpoints (Surface 1 — morning brief)
# ---------------------------------------------------------------------------


class BriefRequest(BaseModel):
    patient_id: str


@app.post("/api/coach/brief")
async def post_coach_brief(req: BriefRequest) -> StreamingResponse:
    """Generate the morning brief and stream it via SSE.

    Streams three events:
    - event: brief  — full BriefPayload as JSON (UI renders the card)
    - event: audio  — base64 audio chunks from Voxtral TTS of raw_text
    - event: done   — terminator
    """
    patient = _PATIENTS_BY_ID.get(req.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient.get("token", patient["id"]),
        name=patient["name"],
        age=patient.get("age"),
    )

    client = _get_mistral()

    async def _stream():
        from backend import coach as _coach

        payload = await _coach.generate_morning_brief(client, patient_ctx)

        yield f"event: brief\ndata: {json.dumps(payload.to_dict(), ensure_ascii=False)}\n\n"

        # stream_voice_events expects an Iterator[str] of tokens; wrap raw_text in one.
        loop = asyncio.get_event_loop()
        try:
            def _text_iter():
                yield payload.raw_text

            audio_chunks = await loop.run_in_executor(
                None,
                lambda: [
                    payload_bytes
                    for kind, payload_bytes in stream_voice_events(
                        _text_iter(), voice_id=DEMO_ASSISTANT_VOICE
                    )
                    if kind == "audio"
                ],
            )
            for chunk_bytes in audio_chunks:
                b64 = base64.b64encode(chunk_bytes).decode("ascii")
                yield f"event: audio\ndata: {json.dumps({'base64_pcm_chunk': b64})}\n\n"
        except Exception:
            logger.exception("TTS streaming failed in /api/coach/brief")

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


class ReplyRequest(BaseModel):
    patient_id: str
    text: str


@app.post("/api/coach/reply")
async def post_coach_reply(req: ReplyRequest) -> dict:
    """Record the user's spoken/typed reply to the morning brief."""
    patient = _PATIENTS_BY_ID.get(req.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient.get("token", patient["id"]),
        name=patient["name"],
        age=patient.get("age"),
    )

    from backend import coach as _coach

    await _coach.record_user_reply(patient_ctx, req.text)
    return {"ok": True, "stored": req.text}


@app.get("/api/dashboard/{patient_id}")
async def get_dashboard(patient_id: str) -> dict:
    """Return the dashboard payload: stats + LLM-generated insights."""
    patient = _PATIENTS_BY_ID.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient.get("token", patient["id"]),
        name=patient["name"],
        age=patient.get("age"),
    )

    client = _get_mistral()

    from backend import coach as _coach

    payload = await _coach.generate_dashboard(client, patient_ctx)
    return payload.to_dict()


# ---------------------------------------------------------------------------
# Surface 3 — notification SSE stream + dev trigger
# ---------------------------------------------------------------------------


@app.get("/api/notifications/stream")
async def notifications_stream() -> StreamingResponse:
    """Long-lived SSE stream — frontend subscribes once and receives every nudge."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)
    _notification_subscribers.add(queue)

    async def _reader():
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                payload = await queue.get()
                yield f"event: notification\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            _notification_subscribers.discard(queue)

    return StreamingResponse(_reader(), media_type="text/event-stream")


class FireNotificationRequest(BaseModel):
    patient_id: str
    metric: str
    value: float


@app.post("/dev/fire-notification")
async def dev_fire_notification(req: FireNotificationRequest) -> dict:
    """DEV ONLY — manually trigger a notification for the demo."""
    patient = _PATIENTS_BY_ID.get(req.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient.get("token", patient["id"]),
        name=patient["name"],
        age=patient.get("age"),
    )

    client = Mistral(api_key=MISTRAL_API_KEY)

    from backend import nudge as _nudge

    message = await _nudge.fire_manual(client, patient_ctx, req.metric, req.value)
    if message is None:
        raise HTTPException(
            status_code=400,
            detail=f"No baseline stored for metric '{req.metric}' — cannot fire",
        )

    await _broadcast_notification(message.to_dict())
    return {"fired": True, "message": message.to_dict()}


# ---------------------------------------------------------------------------
# Onboarding endpoints (Surface 0 — one-time vocal onboarding)
# ---------------------------------------------------------------------------

from backend import onboarding as onboarding_module  # noqa: E402
from backend.onboarding_questions import QUESTIONS as _ONBOARDING_QUESTIONS  # noqa: E402


class OnboardingAnswerPayload(BaseModel):
    question_id: str
    value: Any


def _resolve_patient_ctx(patient_id: str) -> PatientContext:
    patient = _PATIENTS_BY_ID.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")
    return PatientContext(
        token=patient.get("token", patient["id"]),
        name=patient["name"],
        age=patient.get("age"),
    )


def _step_to_payload(step: onboarding_module.OnboardingStep) -> dict:
    q = step.question
    return {
        "index": step.index,
        "total": step.total,
        "done": step.done,
        "question": {
            "id": q.id,
            "section": q.section,
            "text_fr": q.text_fr,
            "text_en": q.text_en,
            "field": q.field,
            "type": q.type,
            "enum_values": list(q.enum_values),
        },
    }


@app.post("/api/onboarding/start/{patient_id}")
async def onboarding_start(patient_id: str) -> dict:
    patient_ctx = _resolve_patient_ctx(patient_id)
    step = onboarding_module.start_session(patient_ctx.token)
    return _step_to_payload(step)


@app.post("/api/onboarding/answer/{patient_id}")
async def onboarding_answer(patient_id: str, payload: OnboardingAnswerPayload) -> dict:
    patient_ctx = _resolve_patient_ctx(patient_id)
    try:
        step = onboarding_module.record_answer(
            patient_ctx.token, payload.question_id, payload.value
        )
    except onboarding_module.OnboardingError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return _step_to_payload(step)


@app.post("/api/onboarding/finalize/{patient_id}")
async def onboarding_finalize(patient_id: str) -> dict:
    patient_ctx = _resolve_patient_ctx(patient_id)
    try:
        onboarding_module.finalize(patient_ctx.token)
    except onboarding_module.OnboardingError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return {"ok": True, "memory_file": f"data/memory/{patient_ctx.token}.md"}


@app.post("/dev/onboarding/seed/{patient_id}")
async def dev_onboarding_seed(
    patient_id: str,
    seed_file: str = "pierre_onboarding.json",
) -> dict:
    """Fill remaining onboarding answers from a seed JSON, then finalize. Dev-only."""
    patient_ctx = _resolve_patient_ctx(patient_id)
    seed_path = _Path("data/seeds") / seed_file
    if not seed_path.exists():
        raise HTTPException(status_code=404, detail=f"seed file not found: {seed_path}")
    seed = json.loads(seed_path.read_text())
    if patient_ctx.token not in onboarding_module._SESSIONS:
        onboarding_module.start_session(patient_ctx.token)
    session = onboarding_module._SESSIONS[patient_ctx.token]
    for q in _ONBOARDING_QUESTIONS:
        if q.id not in session and q.field in seed:
            session[q.id] = seed[q.field]
    try:
        onboarding_module.finalize(patient_ctx.token)
    except onboarding_module.OnboardingError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return {"ok": True, "seeded_from": str(seed_path)}


# ---------------------------------------------------------------------------
# Vocal intake (free-speech onboarding) — new patient form with 5 categories
# ---------------------------------------------------------------------------

from backend import blood_ocr, memory as memory_module, vocal_intake  # noqa: E402


class IntakeStartRequest(BaseModel):
    patient_id: str


class IntakeTextRequest(BaseModel):
    session_id: str
    transcript: str


class IntakeFinalizeRequest(BaseModel):
    session_id: str


@app.get("/api/intake/schema")
async def intake_schema() -> dict:
    """Return the 5-category form schema (static, no session needed)."""
    return {"categories": vocal_intake.schema_to_dict()}


@app.post("/api/intake/start")
async def intake_start(req: IntakeStartRequest) -> dict:
    """Open a new vocal intake session for a patient."""
    session = vocal_intake.start(req.patient_id)
    return vocal_intake.form_state(session)


@app.post("/api/intake/audio")
async def intake_audio(
    session_id: str,
    audio: UploadFile = File(...),
) -> dict:
    """Transcribe one utterance, extract fields, merge into the form.

    The frontend calls this with a short audio clip each time the user
    pauses (push-to-talk or VAD segment). The response includes the full
    form state so the page can re-render all filled fields.
    """
    session = vocal_intake.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="intake session not found")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="empty audio")

    client = _get_mistral()
    loop = asyncio.get_running_loop()
    try:
        transcript = await loop.run_in_executor(None, transcribe, client, audio_bytes)
    except Exception as exc:
        logger.exception("intake STT failed")
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc

    return await loop.run_in_executor(
        None, vocal_intake.ingest, session, client, transcript or ""
    )


@app.post("/api/intake/text")
async def intake_text(req: IntakeTextRequest) -> dict:
    """Dev/test hook: ingest a transcript directly (bypasses Voxtral STT)."""
    session = vocal_intake.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="intake session not found")

    client = _get_mistral()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, vocal_intake.ingest, session, client, req.transcript
    )


@app.post("/api/intake/finalize")
async def intake_finalize(req: IntakeFinalizeRequest) -> dict:
    """Persist the extracted form to the patient's memory file."""
    try:
        return vocal_intake.finalize(req.session_id)
    except RuntimeError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


# ---------------------------------------------------------------------------
# Blood panel PDF OCR
# ---------------------------------------------------------------------------


@app.post("/api/blood-panel/upload")
async def blood_panel_upload(pdf: UploadFile = File(...)) -> dict:
    """Upload a blood panel PDF, OCR it with Mistral, extract biomarkers.

    Returns:
        biomarkers: dict of {key: {value, unit}} for every biomarker found
        markdown:   the full OCR markdown (useful for the frontend preview)
        page_count: number of OCR'd pages
    """
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="empty pdf")
    filename = pdf.filename or "bilan.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="expected a .pdf file")

    client = _get_mistral()
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None, blood_ocr.process_blood_panel, client, pdf_bytes, filename
        )
    except Exception as exc:
        logger.exception("blood panel OCR failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Challenges + Bookings — read endpoints for dedicated frontend pages
# ---------------------------------------------------------------------------


@app.get("/api/challenges/{patient_id}")
async def list_challenges(patient_id: str) -> dict:
    """Return the patient's personalized challenges, split by status.

    Shape:
        {
          "active":  [ {date, title, metric, target, status, reason}, ... ],
          "history": [ ...non-active challenges... ],
          "total":   int
        }
    """
    patient_ctx = _resolve_patient_ctx(patient_id)
    all_challenges = memory_module.read_all_challenges(patient_ctx.token)
    active = [c for c in all_challenges if c["status"] == "active"]
    history = [c for c in all_challenges if c["status"] != "active"]
    return {
        "active": active,
        "history": history,
        "total": len(all_challenges),
    }


@app.get("/api/bookings/{patient_id}")
async def list_bookings(patient_id: str) -> dict:
    """Return every consultation booking made for the patient, oldest first.

    Shape:
        {
          "bookings": [
            {
              "created_at": "2026-04-11",
              "specialty": "ORL",
              "professional": "Dr. Camille Rousseau",
              "location": "Paris 9e",
              "slot": "aujourd'hui 17h30",
              "urgency": "urgent",
              "status": "confirmed",
              "reason": "..."
            }, ...
          ],
          "total": int
        }
    """
    patient_ctx = _resolve_patient_ctx(patient_id)
    bookings = memory_module.read_bookings(patient_ctx.token)
    return {"bookings": bookings, "total": len(bookings)}


# ---------------------------------------------------------------------------
# Legacy endpoints (kept for HealthKit + compat)
# ---------------------------------------------------------------------------


@app.post("/health")
async def receive_health_data(payload: HealthPayload):
    """Receive health metrics from Apple Shortcuts."""
    if not payload.metrics:
        raise HTTPException(status_code=400, detail="No metrics provided")
    loop = asyncio.get_running_loop()
    count = await loop.run_in_executor(None, insert_metrics, payload.metrics)
    return {"status": "ok", "inserted": count}


@app.get("/health/ping")
async def ping():
    return {"status": "alive"}


@app.websocket("/voice/ws")
async def voice_ws(ws: WebSocket):
    """Realtime voice loop — bidirectional WebSocket."""
    await handle_voice_ws(ws)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_protocol(
    llm_text: str | None,
    burnout: BurnoutResult | None,
) -> list[str]:
    """Extract or generate 3 protocol actions based on context."""
    # Default fallback protocol based on burnout level
    if burnout and burnout.level == "high":
        return [
            "Couche-toi avant 22h30 ce soir",
            "30 min de marche, pas de cardio intense",
            "Prends 5 min de respiration guidée",
        ]
    if burnout and burnout.level == "moderate":
        return [
            "Vise 7h de sommeil cette nuit",
            "30 min d'activité physique modérée",
            "Fais une pause de 10 min cet après-midi",
        ]
    return [
        "Continue comme ça, bon rythme",
        "30 min d'exercice au choix",
        "Garde un horaire de coucher régulier",
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Entry point for vital-server."""
    init_db()
    uvicorn_run(
        "backend.health_server:app",
        host=HEALTH_SERVER_HOST,
        port=HEALTH_SERVER_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
