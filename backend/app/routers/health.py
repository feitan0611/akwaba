from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings
from app.deps import get_app_settings, get_engines
from app.languages import LOCAL_LANGUAGES, PIVOT_LANGUAGES
from app.schemas import HealthResponse, LanguageInfo
from app.services.registry import Engines

router = APIRouter(tags=["Système"])


@router.get("/health", response_model=HealthResponse, summary="État du service")
def health(settings: Settings = Depends(get_app_settings), engines: Engines = Depends(get_engines)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        engine=settings.engine,
        pivot_language=settings.pivot_language,
        models={brick.task: brick.name for brick in engines.bricks}
        | ({"embedding": engines.retriever.embedder.name} if engines.retriever else {}),
        capabilities=engines.capabilities(),
    )


@router.get("/languages", response_model=list[LanguageInfo], summary="Langues prises en charge")
def languages() -> list[LanguageInfo]:
    return [LanguageInfo(code=c, name=n, role="local") for c, n in LOCAL_LANGUAGES.items()] + [
        LanguageInfo(code=c, name=n, role="pivot") for c, n in PIVOT_LANGUAGES.items()
    ]
