import base64
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from fastapi.concurrency import run_in_threadpool

from app.deps import get_engines
from app.schemas import SpeechRequest, SpeechResponse
from app.services.registry import Engines

router = APIRouter(tags=["Briques IA"])


@router.post(
    "/speech",
    response_model=SpeechResponse,
    summary="Synthèse vocale (TTS)",
    responses={200: {"content": {"audio/wav": {}}, "description": "JSON Base64 ou fichier WAV brut"}},
)
async def speech(
    body: SpeechRequest,
    response_format: Literal["base64", "binary"] = Query(
        "base64", description="base64 : JSON avec l'audio encodé ; binary : fichier audio/wav brut"
    ),
    engines: Engines = Depends(get_engines),
) -> SpeechResponse | Response:
    wav = await run_in_threadpool(engines.synthesizer.synthesize, body.text, body.language, body.voice_id)
    if response_format == "binary":
        return Response(content=wav, media_type="audio/wav")
    return SpeechResponse(
        audio_base64=base64.b64encode(wav).decode("ascii"),
        language=body.language,
        voice_id=body.voice_id,
        engine=engines.synthesizer.name,
    )
