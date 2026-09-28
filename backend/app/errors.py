"""Format d'erreur unique pour toute l'API : {"error": {"code": ..., "message": ..., "details": ...}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _error_body(code: str, message: str, details: list | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


def register_error_handlers(app: FastAPI) -> None:
    # Import local : app.services.base dépend (via app.audio) de ce module.
    from app.rag.documents import KnowledgeBaseError
    from app.services.base import (
        EngineError,
        EngineUnavailableError,
        InvalidInputError,
        LanguageNotSupportedError,
        LanguageRequiredError,
    )

    # Erreurs des briques IA → (statut HTTP, code d'erreur). Ordre : du plus précis au plus général.
    engine_errors = [
        (LanguageNotSupportedError, 422, "language_not_supported"),
        (LanguageRequiredError, 422, "language_required"),
        (InvalidInputError, 400, "invalid_input"),
        (EngineUnavailableError, 503, "engine_unavailable"),
        # Document mal formé dans knowledge/ : le message nomme le fichier à corriger.
        (KnowledgeBaseError, 500, "knowledge_base_error"),
    ]

    @app.exception_handler(EngineError)
    async def handle_engine_error(_: Request, exc: EngineError) -> JSONResponse:
        for error_type, status, code in engine_errors:
            if isinstance(exc, error_type):
                return JSONResponse(status_code=status, content=_error_body(code, str(exc)))
        logger.exception("Erreur de moteur IA", exc_info=exc)
        return JSONResponse(status_code=500, content=_error_body("engine_error", "Erreur du moteur IA."))

    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    # Erreurs HTTP levées par FastAPI/Starlette elles-mêmes (corps illisible, route inconnue…) :
    # sans ce gestionnaire, elles sortiraient au format {"detail": ...} au lieu du format unique.
    http_codes = {400: "invalid_request", 404: "not_found", 405: "method_not_allowed"}

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = http_codes.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Erreur HTTP."
        return JSONResponse(status_code=exc.status_code, content=_error_body(code, message), headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": [str(part) for part in err.get("loc", ())], "msg": err.get("msg", "")} for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Requête invalide.", details),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # On journalise le détail côté serveur mais on ne l'expose jamais au client.
        logger.exception("Erreur interne non gérée", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "Erreur interne du serveur."),
        )
