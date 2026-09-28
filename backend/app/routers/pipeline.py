"""Endpoint de bout en bout : audio local → réponse vocale dans la même langue.

Enchaîne : détection/transcription → traduction vers la langue pivot → LLM →
traduction retour → synthèse vocale. C'est l'endpoint utilisé par le démonstrateur.
"""

import base64
import time

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from app.audio import AUDIO_REQUEST_BODY, read_audio_input
from app.config import Settings
from app.deps import get_app_settings, get_engines
from app.schemas import DetectResponse, PipelineResponse
from app.services.registry import Engines

router = APIRouter(tags=["Pipeline"])


async def _timed(timings: dict[str, float], step: str, func, *args):
    start = time.perf_counter()
    result = await run_in_threadpool(func, *args)
    timings[step] = round((time.perf_counter() - start) * 1000, 2)
    return result


@router.post(
    "/pipeline",
    response_model=PipelineResponse,
    summary="Audio (Baoulé/Dioula) → réponse vocale dans la même langue",
    openapi_extra=AUDIO_REQUEST_BODY,
)
async def pipeline(
    request: Request,
    engines: Engines = Depends(get_engines),
    settings: Settings = Depends(get_app_settings),
) -> PipelineResponse:
    audio = await read_audio_input(request, settings.max_audio_bytes)
    pivot = settings.pivot_language
    timings: dict[str, float] = {}

    detected = await _timed(timings, "detect", engines.recognizer.transcribe, audio)
    question_pivot = await _timed(
        timings, "translate_in", engines.translator.translate, detected.text, detected.language, pivot
    )
    answer_pivot = await _timed(timings, "ask", engines.responder.answer, question_pivot, pivot)
    answer_text = await _timed(
        timings, "translate_out", engines.translator.translate, answer_pivot, pivot, detected.language
    )
    wav = await _timed(
        timings, "speech", engines.synthesizer.synthesize, answer_text, detected.language, audio.options.get("voice_id")
    )

    return PipelineResponse(
        detection=DetectResponse(
            text=detected.text,
            language=detected.language,
            confidence=detected.confidence,
            language_source=detected.language_source,
            engine=engines.recognizer.name,
        ),
        pivot_language=pivot,
        question_pivot=question_pivot,
        answer_pivot=answer_pivot,
        answer_text=answer_text,
        answer_audio_base64=base64.b64encode(wav).decode("ascii"),
        timings_ms=timings,
    )
