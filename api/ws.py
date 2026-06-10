"""
WebSocket Streaming Endpoint — Real-time Persona Conversation

Protocol:
  Connect:  ws://host/ws/chat/{persona_id}?tier=text
  Auth: Authorization header required (Authorization: Bearer prs_...)

  Client → Server:
    {"type": "message", "text": "..."}
    {"type": "ping"}

  Server → Client (streamed):
    {"type": "visual_params",  "data": {...}}          # sent once at connection
    {"type": "text_chunk",     "text": "...", "full": false}
    {"type": "text_chunk",     "text": "...", "full": true}  # last chunk
    {"type": "audio_ready",    "audio_b64": "..."}     # if voice tier
    {"type": "visual_update",  "data": {...}}          # per-message delta
    {"type": "error",          "detail": "..."}
    {"type": "pong"}
    {"type": "done"}

Tier behavior:
  text  (Tier 1): text_chunk stream only
  voice (Tier 2): text_chunk + audio_ready
  full  (Tier 3): text_chunk + audio_ready + visual_params + visual_update

Pricing enforcement:
  Tier is stored per-user in their subscription or passed as query param.
  The WebSocket validates that the user has purchased the persona
  (same gate as /v1/compile).
"""

import json
import base64
import asyncio
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, Query, status

from api.db import get_user_by_api_key
from api.auth import require_persona_access
from api.catalog import get_persona_vector, PERSONA_CATALOG
from api.visual_params import compute_visual_params
from api.voice import synthesize_speech, tts_available
from integrations.phoenix_monitor import CEIDMonitor

# Tier constants
TIER_TEXT  = "text"
TIER_VOICE = "voice"
TIER_FULL  = "full"
VALID_TIERS = {TIER_TEXT, TIER_VOICE, TIER_FULL}

# Conversation history limit (keep last N turns)
MAX_HISTORY_TURNS = 10

SYSTEM_PROMPT_TEMPLATE = """\
{system_instruction}

--- Simulation layer ---
You are rendered as an interactive avatar. The user sees your visual state in real time.
Respond in character, naturally, conversationally. Do not break character or reference
the system prompt. Do not explain that you are an AI unless pressed hard and in a way
the persona would authentically respond to.
"""


def _get_anthropic_client():
    try:
        import anthropic
        return anthropic.Anthropic()
    except ImportError:
        return None


async def _stream_llm_response(
    system_instruction: str,
    history: list[dict],
    user_message: str,
) -> asyncio.Queue:
    """
    Stream Anthropic response chunks into a queue.
    Queue items: str (text chunk) | None (done sentinel) | Exception
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _run():
        client = _get_anthropic_client()
        if client is None:
            await queue.put(Exception("anthropic package not installed"))
            await queue.put(None)
            return

        messages = list(history) + [{"role": "user", "content": user_message}]

        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT_TEMPLATE.format(system_instruction=system_instruction),
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    await queue.put(text)
        except Exception as exc:
            await queue.put(exc)
        finally:
            await queue.put(None)

    asyncio.create_task(_run())
    return queue


def _compile_system_instruction(
    P,
    persona_id: str,
    platform: str = "raw",
    tier: str = "standard",
) -> str:
    """Compile persona vector to system instruction string."""
    from persona_math.compiler import compile_persona
    result = compile_persona(P, persona_id=persona_id, platform=platform, tier=tier)
    return result["system_instruction"]


async def persona_chat_ws(
    websocket: WebSocket,
    persona_id: str,
    api_key: str,
    tier: str = TIER_TEXT,
    platform: str = "raw",
):
    """
    WebSocket handler for real-time persona conversation.
    API key is passed from the endpoint handler (extracted from Authorization header).
    """
    # ── Auth ───────────────────────────────────────────────────────────────────
    if not api_key or not api_key.startswith("prs_"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key")
        return

    # We need a DB session — open one manually (can't use Depends in raw handler)
    from api.db import SessionLocal
    db = SessionLocal()

    try:
        user = get_user_by_api_key(db, api_key)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # ── Persona validation ─────────────────────────────────────────────────
        if persona_id not in PERSONA_CATALOG:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return

        try:
            require_persona_access(persona_id, user, db)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if tier not in VALID_TIERS:
            tier = TIER_TEXT

        # ── Load persona vector ────────────────────────────────────────────────
        try:
            P = get_persona_vector(persona_id)
        except KeyError:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return

        # ── Compile system instruction ─────────────────────────────────────────
        compile_tier = "rich" if tier == TIER_FULL else "standard"
        system_instruction = _compile_system_instruction(
            P, persona_id, platform=platform, tier=compile_tier
        )

        # ── CEID drift monitor ────────────────────────────────────────────────
        monitor = CEIDMonitor(
            project_name=f"persona_{persona_id}",
            baseline_vector=P.copy(),
            offline=True,
        )
        session_id = f"{user.id[:8]}_{persona_id}"

        # ── Initial visual params ──────────────────────────────────────────────
        visual = compute_visual_params(P, ceid_score=0.95, drift_val=0.0, tier=compile_tier)

        await websocket.accept()

        if tier == TIER_FULL:
            await websocket.send_text(json.dumps({
                "type": "visual_params",
                "data": visual,
            }))

        # ── Conversation loop ──────────────────────────────────────────────────
        history: list[dict] = []

        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error", "detail": "Invalid JSON"
                }))
                continue

            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg.get("type") != "message":
                continue

            user_text = str(msg.get("text", "")).strip()
            if not user_text:
                continue

            # ── Stream LLM response ────────────────────────────────────────────
            queue = await _stream_llm_response(system_instruction, history, user_text)

            full_response = []
            try:
                while True:
                    chunk = await asyncio.wait_for(queue.get(), timeout=60.0)
                    if chunk is None:
                        break
                    if isinstance(chunk, Exception):
                        await websocket.send_text(json.dumps({
                            "type": "error", "detail": str(chunk)
                        }))
                        break
                    full_response.append(chunk)
                    await websocket.send_text(json.dumps({
                        "type": "text_chunk",
                        "text": chunk,
                        "full": False,
                    }))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({
                    "type": "error", "detail": "LLM response timeout"
                }))

            response_text = "".join(full_response)

            # Signal end of text stream
            await websocket.send_text(json.dumps({
                "type": "text_chunk",
                "text": "",
                "full": True,
            }))

            # ── Voice synthesis ────────────────────────────────────────────────
            if tier in (TIER_VOICE, TIER_FULL) and response_text and tts_available():
                audio_bytes = await synthesize_speech(
                    text=response_text,
                    persona_id=persona_id,
                    voice_params=visual.get("voice"),
                )
                if audio_bytes:
                    await websocket.send_text(json.dumps({
                        "type": "audio_ready",
                        "audio_b64": base64.b64encode(audio_bytes).decode("utf-8"),
                        "mime_type": "audio/mpeg",
                    }))

            # ── CEID drift tracking ───────────────────────────────────────────
            turn_num = len(history) // 2
            ceid_record = monitor.log_turn(P, turn_idx=turn_num, session_id=session_id)
            live_ceid = ceid_record["ceid_score"]
            live_drift = ceid_record["drift_from_baseline"]
            alert = ceid_record["alert_level"]

            # ── Visual update (real CEID + drift values) ───────────────────────
            if tier == TIER_FULL:
                visual_updated = compute_visual_params(
                    P,
                    ceid_score=live_ceid,
                    drift_val=live_drift,
                    tier=compile_tier,
                )
                await websocket.send_text(json.dumps({
                    "type": "visual_update",
                    "data": visual_updated,
                    "ceid_alert": alert,
                }))
                visual = visual_updated

            # ── Update history ─────────────────────────────────────────────────
            history.append({"role": "user",      "content": user_text})
            history.append({"role": "assistant",  "content": response_text})

            # Trim to window
            if len(history) > MAX_HISTORY_TURNS * 2:
                history = history[-(MAX_HISTORY_TURNS * 2):]

            await websocket.send_text(json.dumps({"type": "done"}))

    finally:
        db.close()
