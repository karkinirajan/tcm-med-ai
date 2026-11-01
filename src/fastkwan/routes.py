import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from .config import NotConfigured
from .schemas import (
    LifestyleResponse,
    PrescriptionResponse,
    Query,
    RankedItem,
    SyndromeResponse,
)
from .security import require_api_key
from .text import reorder_syndrome_text

logger = logging.getLogger(__name__)

public = APIRouter()
protected = APIRouter(dependencies=[Depends(require_api_key)])


def services(request: Request):
    return request.app.state.services


def upstream_failure(error):
    """The old handlers returned ``str(error)`` of whatever went wrong (client messages included)
    to the caller. The details go to the log; the caller gets a fixed message."""
    logger.exception("An upstream service failed", exc_info=error)
    return HTTPException(502, "An upstream service (OpenAI, Pinecone, Cohere or MongoDB) failed.")


def candidates(query, namespace, k, services_):
    """Symptoms extracted from the description, vector search, and the texts found."""
    symptoms = services_.ner().extract(query)
    knowledge = services_.knowledge()
    search_text = symptoms or query  # nothing recognised: search with the description itself
    return search_text, knowledge, knowledge.search(search_text, namespace, k)


@protected.post("/syndrome", response_model=SyndromeResponse)
def syndrome(body: Query, services_=Depends(services)):
    """Syndrome differentiation: symptoms, then vector search and reranking of similar syndromes."""
    settings = services_.settings
    try:
        search_text, knowledge, texts = candidates(
            body.query, settings.syndromes_namespace, settings.syndrome_candidates, services_
        )
        if not texts:
            return SyndromeResponse(result="No matching syndromes found.")
        ranked = knowledge.rerank(search_text, texts, settings.rerank_top_n)
    except NotConfigured:
        raise  # answered with a 503 that names the missing variables
    except Exception as error:  # noqa: BLE001 - mapped to one clear answer, details are logged
        raise upstream_failure(error) from error
    return SyndromeResponse(result=reorder_syndrome_text(" ".join(item.text for item in ranked)))


@protected.post("/lifestyle", response_model=LifestyleResponse)
def lifestyle(body: Query, services_=Depends(services)):
    """Prevention and lifestyle advice for a disease, found by (partial) name."""
    try:
        found = services_.diseases().find(body.query)
    except NotConfigured:
        raise
    except Exception as error:  # noqa: BLE001
        raise upstream_failure(error) from error
    if found is None:
        raise HTTPException(404, "Disease not found")
    return found


@protected.post(
    "/prescription", response_model=PrescriptionResponse, response_model_exclude_none=True
)
def prescription(body: Query, services_=Depends(services)):
    """Prescription suggestions: symptoms, then vector search and reranking."""
    settings = services_.settings
    try:
        search_text, knowledge, texts = candidates(
            body.query,
            settings.prescriptions_namespace,
            settings.prescription_candidates,
            services_,
        )
        if not texts:
            return PrescriptionResponse(results=[], message="No matching prescriptions found")
        ranked = knowledge.rerank(search_text, texts, settings.rerank_top_n)
    except NotConfigured:
        raise
    except Exception as error:  # noqa: BLE001
        raise upstream_failure(error) from error
    return PrescriptionResponse(
        results=[
            RankedItem(text=item.text, index=item.index, relevance_score=item.score)
            for item in ranked
        ]
    )


@public.get("/")
def root():
    return {"message": "FastKwan TCM API", "version": "1.0.0", "docs": "/docs"}


@public.get("/health")
def health():
    return {"status": "healthy"}
