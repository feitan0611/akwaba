from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.deps import get_engines
from app.schemas import AskRequest, AskResponse
from app.services.registry import Engines

router = APIRouter(tags=["Briques IA"])


@router.post("/ask", response_model=AskResponse, summary="Réponse à une requête en langue pivot (LLM)")
async def ask(body: AskRequest, engines: Engines = Depends(get_engines)) -> AskResponse:
    text = await run_in_threadpool(engines.responder.answer, body.text, body.language)
    return AskResponse(text=text, language=body.language, engine=engines.responder.name)
