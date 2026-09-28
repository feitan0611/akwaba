"""Base de connaissances (RAG) : consulter l'index et tester la recherche par embeddings."""

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.deps import get_engines
from app.errors import APIError
from app.rag.index import Retriever
from app.schemas import (
    KnowledgeDocumentInfo,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatus,
    SearchResult,
)
from app.services.registry import Engines

router = APIRouter(prefix="/knowledge", tags=["Base de connaissances (RAG)"])


def get_retriever(engines: Engines = Depends(get_engines)) -> Retriever:
    if engines.retriever is None:
        raise APIError(503, "rag_disabled", "Le RAG est désactivé sur ce serveur (LANGCI_RAG_ENABLED=false).")
    return engines.retriever


def _status(retriever: Retriever, force_rebuild: bool = False) -> KnowledgeStatus:
    index = retriever.index(force_rebuild=force_rebuild)
    documents: dict[str, KnowledgeDocumentInfo] = {}
    for chunk in index.chunks:
        info = documents.setdefault(
            chunk.doc_id, KnowledgeDocumentInfo(doc_id=chunk.doc_id, title=chunk.title, source=chunk.source, chunks=0)
        )
        info.chunks += 1
    return KnowledgeStatus(
        embedder=retriever.embedder.name,
        min_score=retriever.min_score,
        top_k=retriever.top_k,
        chunks=len(index.chunks),
        documents=list(documents.values()),
    )


@router.get("", response_model=KnowledgeStatus, summary="Documents indexés et réglages du RAG")
async def knowledge_status(retriever: Retriever = Depends(get_retriever)) -> KnowledgeStatus:
    return await run_in_threadpool(_status, retriever)


@router.post("/search", response_model=KnowledgeSearchResponse, summary="Tester la recherche par embeddings")
async def knowledge_search(
    body: KnowledgeSearchRequest, retriever: Retriever = Depends(get_retriever)
) -> KnowledgeSearchResponse:
    passages = await run_in_threadpool(retriever.retrieve, body.query, body.top_k, body.min_score)
    return KnowledgeSearchResponse(
        embedder=retriever.embedder.name,
        min_score=retriever.min_score if body.min_score is None else body.min_score,
        results=[SearchResult.model_validate(p, from_attributes=True) for p in passages],
    )


@router.post("/reindex", response_model=KnowledgeStatus, summary="Reconstruire l'index")
async def knowledge_reindex(retriever: Retriever = Depends(get_retriever)) -> KnowledgeStatus:
    return await run_in_threadpool(_status, retriever, True)
