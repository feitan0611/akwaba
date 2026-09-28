from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from app.audio import AUDIO_REQUEST_BODY, read_audio_input
from app.config import Settings
from app.deps import get_app_settings, get_engines
from app.schemas import DetectResponse
from app.services.registry import Engines

router = APIRouter(tags=["Briques IA"])


@router.post(
    "/detect",
    response_model=DetectResponse,
    summary="Transcription + détection de langue (STT/ASR)",
    openapi_extra=AUDIO_REQUEST_BODY,
)
async def detect(
    request: Request,
    engines: Engines = Depends(get_engines),
    settings: Settings = Depends(get_app_settings),
) -> DetectResponse:
    audio = await read_audio_input(request, settings.max_audio_bytes)
    result = await run_in_threadpool(engines.recognizer.transcribe, audio)
    return DetectResponse(
        text=result.text,
        language=result.language,
        confidence=result.confidence,
        language_source=result.language_source,
        engine=engines.recognizer.name,
    )
