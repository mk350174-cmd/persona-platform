"""
ElevenLabs TTS integration for persona voices.

Each persona has a pre-assigned ElevenLabs voice character.
Voice params (stability, similarity_boost, style) are driven
by the HPEP-100 vector in real time via visual_params.py.

Env vars:
  ELEVENLABS_API_KEY   — required for TTS in Voice/Full tiers
  ELEVENLABS_MODEL     — defaults to 'eleven_turbo_v2_5'
"""

import os
import hashlib
from pathlib import Path
from typing import AsyncIterator, Optional

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL   = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
AUDIO_CACHE_DIR    = Path("/tmp/persona_audio")

# Per-persona ElevenLabs voice IDs (configurable via env)
PERSONA_VOICE_IDS: dict[str, str] = {
    "machiavelli": os.getenv("VOICE_MACHIAVELLI", "ErXwobaYiN019PkySvjV"),  # Antoni
    "kant":        os.getenv("VOICE_KANT",        "VR6AewLTigWG4xSOukaG"),  # Arnold
    "holmes":      os.getenv("VOICE_HOLMES",      "pNInz6obpgDQGcFmaJgB"),  # Adam
}

DEFAULT_VOICE_ID = "ErXwobaYiN019PkySvjV"


def _get_voice_id(persona_id: str) -> str:
    return PERSONA_VOICE_IDS.get(persona_id, DEFAULT_VOICE_ID)


def _audio_cache_path(text: str, persona_id: str, voice_params: dict) -> Path:
    """Deterministic cache path based on text + persona + voice params."""
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = f"{persona_id}|{text}|{voice_params}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return AUDIO_CACHE_DIR / f"{persona_id}_{digest}.mp3"


async def synthesize_speech(
    text: str,
    persona_id: str,
    voice_params: Optional[dict] = None,
) -> Optional[bytes]:
    """
    Convert text to speech using ElevenLabs API.

    Parameters
    ----------
    text        : text to synthesize
    persona_id  : persona key for voice ID lookup
    voice_params: dict from visual_params["voice"] with stability, similarity_boost, style_exaggeration

    Returns
    -------
    MP3 bytes, or None if API key not set / API unavailable
    """
    if not ELEVENLABS_API_KEY:
        return None

    if voice_params is None:
        voice_params = {"stability": 0.65, "similarity_boost": 0.75, "style_exaggeration": 0.2}

    cache_path = _audio_cache_path(text, persona_id, str(voice_params))
    if cache_path.exists():
        return cache_path.read_bytes()

    try:
        import httpx

        voice_id = _get_voice_id(persona_id)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability":            voice_params.get("stability", 0.65),
                "similarity_boost":     voice_params.get("similarity_boost", 0.75),
                "style":                voice_params.get("style_exaggeration", 0.2),
                "use_speaker_boost":    True,
            },
        }

        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            audio_bytes = resp.content

        cache_path.write_bytes(audio_bytes)
        return audio_bytes

    except Exception:
        return None


async def synthesize_stream(
    text: str,
    persona_id: str,
    voice_params: Optional[dict] = None,
) -> AsyncIterator[bytes]:
    """
    Streaming TTS — yields audio chunks as they arrive from ElevenLabs.
    Falls back to synthesize_speech (single request) if streaming unavailable.
    """
    if not ELEVENLABS_API_KEY:
        return

    if voice_params is None:
        voice_params = {"stability": 0.65, "similarity_boost": 0.75, "style_exaggeration": 0.2}

    try:
        import httpx

        voice_id = _get_voice_id(persona_id)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability":        voice_params.get("stability", 0.65),
                "similarity_boost": voice_params.get("similarity_boost", 0.75),
                "style":            voice_params.get("style_exaggeration", 0.2),
                "use_speaker_boost": True,
            },
        }

        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    yield chunk

    except Exception:
        # Fall back: synthesize full audio then yield it at once
        audio = await synthesize_speech(text, persona_id, voice_params)
        if audio:
            yield audio


def tts_available() -> bool:
    """True if ElevenLabs key is configured."""
    return bool(ELEVENLABS_API_KEY)
