from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.deps import get_engines
from app.schemas import TranslateRequest, TranslateResponse
from app.services.registry import Engines

router = APIRouter(tags=["Briques IA"])


@router.post(
    "/translate",
    response_model=TranslateResponse,
    summary="Traduction automatique (remplace /translate1 et /translate2 du cahier des charges)",
)
async def translate(body: TranslateRequest, engines: Engines = Depends(get_engines)) -> TranslateResponse:
    text = await run_in_threadpool(engines.translator.translate, body.text, body.source, body.target)
    return TranslateResponse(text=text, source=body.source, target=body.target, engine=engines.translator.name)
