from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings
from app.deps import get_app_settings
from app.languages import LOCAL_LANGUAGES, PIVOT_LANGUAGES
from app.schemas import HealthResponse, LanguageInfo

router = APIRouter(tags=["Système"])


@router.get("/health", response_model=HealthResponse, summary="État du service")
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, engine=settings.engine)


@router.get("/languages", response_model=list[LanguageInfo], summary="Langues prises en charge")
def languages() -> list[LanguageInfo]:
    return [LanguageInfo(code=c, name=n, role="local") for c, n in LOCAL_LANGUAGES.items()] + [
        LanguageInfo(code=c, name=n, role="pivot") for c, n in PIVOT_LANGUAGES.items()
    ]
