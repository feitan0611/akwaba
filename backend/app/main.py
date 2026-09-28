"""Point d'entrée de l'API.

Lancement (depuis le dossier backend/) :  uvicorn app.main:app --reload
Documentation interactive :               http://127.0.0.1:8000/docs
Démonstrateur :                           http://127.0.0.1:8000/demo/
"""

import logging
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import Settings, get_settings
from app.errors import register_error_handlers
from app.routers import ask, detect, health, pipeline, speech, translate
from app.services.registry import build_engines

API_PREFIX = "/api/v1"
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


class NoCacheStaticFiles(StaticFiles):
    """Fichiers du démonstrateur : le navigateur revalide à chaque chargement, pour ne jamais
    afficher une ancienne version du frontend après une mise à jour."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


DESCRIPTION = """
Prototype d'API de traitement vocal du **Baoulé** (`bci`) et du **Dioula** (`dyu`).

Flux principal (`/pipeline`) : audio → détection + transcription → traduction vers la langue
pivot → LLM → traduction retour → synthèse vocale.

Moteurs : `mock` (réponses factices, pour le développement) ou `local` (vrais modèles open source).
Consultez `GET /api/v1/health` → `capabilities` pour savoir ce qui est disponible pour chaque langue.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO)

    app = FastAPI(title=settings.app_name, version=__version__, description=DESCRIPTION)
    app.state.settings = settings
    app.state.engines = build_engines(settings)
    if settings.preload_models:
        # En tâche de fond : le serveur répond tout de suite ; les requêtes attendront le chargement.
        threading.Thread(target=app.state.engines.warmup, name="warmup", daemon=True).start()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    for module in (health, detect, translate, ask, speech, pipeline):
        app.include_router(module.router, prefix=API_PREFIX)

    if settings.serve_demo and FRONTEND_DIR.is_dir():
        app.mount("/demo", NoCacheStaticFiles(directory=FRONTEND_DIR, html=True), name="demo")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
