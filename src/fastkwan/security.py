import secrets

from fastapi import Header, HTTPException, Request, status


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)):
    """When ``API_KEY`` is set, callers must send it as ``X-API-Key``. The service passes patients'
    symptom descriptions to OpenAI, Pinecone and Cohere and costs money per call, and the old code
    had no access control at all."""
    expected = request.app.state.settings.api_key
    if expected and not secrets.compare_digest(x_api_key or "", expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid X-API-Key header is required.")
