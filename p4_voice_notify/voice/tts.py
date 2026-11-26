import os
import httpx

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_BY_LANG = {
    "en": "21m00Tcm4TlvDq8ikWAM",
    "hi": "pNInz6obpgDQGcFmaJgB",
    "kn": "pNInz6obpgDQGcFmaJgB",
    "mr": "pNInz6obpgDQGcFmaJgB",
}

async def speak(text: str, language: str = "en") -> bytes:
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not configured")
    voice_id = VOICE_BY_LANG.get(language, VOICE_BY_LANG["en"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": "eleven_multilingual_v2"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.content