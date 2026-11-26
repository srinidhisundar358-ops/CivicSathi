from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from p4_voice_notify.voice.tts import speak

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str
    language: str = "en"

@router.post("/voice/speak")
async def voice_speak(req: SpeakRequest):
    try:
        audio = await speak(req.text, req.language)
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))