"""Dépendances FastAPI partagées par les routeurs."""

from fastapi import Request

from app.config import Settings
from app.services.registry import Engines


def get_engines(request: Request) -> Engines:
    return request.app.state.engines


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings
