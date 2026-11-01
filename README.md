# FastKwan

A FastAPI service for Traditional Chinese Medicine (TCM): **syndrome differentiation**, **lifestyle advice** for a disease, and **prescription suggestions**, built on OpenAI (symptom extraction), Pinecone (vector search), Cohere (reranking) and MongoDB Atlas (disease texts).

> This is a research and decision-support prototype. Its answers are retrieved texts, not medical advice.

## How it works

| Endpoint | What it does |
|---|---|
| `POST /syndrome` | A chat model extracts the symptoms (NER) from the patient's description, Pinecone finds similar syndromes (30 candidates), Cohere reranks them (top 5), and each entry is reordered so the syndrome type (證型) comes before its symptoms (症狀). |
| `POST /prescription` | The same symptoms, searched in the prescriptions namespace (50 candidates), reranked, returned with their index and relevance score. |
| `POST /lifestyle` | An Atlas Search autocomplete on the disease name returns the disease and its prevention and lifestyle advice (预防与调摄). 404 when nothing matches. |
| `GET /`, `GET /health` | Service info and a health check (always open). |

Request body for the three `POST` endpoints: `{"query": "..."}` (1 to 4000 characters). Swagger UI is at `/docs`.

If nothing is recognised as a symptom, the description itself is searched. Upstream failures answer **502** with a fixed message (the details go to the server log, not to the caller). A missing setting answers **503** and names the variables to set.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) (Python 3.13).

```bash
uv sync
cp .env.example .env        # fill in the keys; the demo values only show the format
uv run fastkwan             # http://127.0.0.1:8000/docs
```

Nothing is required to *start* the server. Without keys, `/health` works and the other endpoints answer 503 with the names of the missing variables.

```bash
curl -X POST http://127.0.0.1:8000/syndrome \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query": "患者咳嗽，喉咙痛，有痰，鼻塞"}'
```

## Configuration

Environment variables, or a local `.env`. [`.env.example`](./.env.example) lists all of them with demo values.

| Variable | Default | Meaning |
|---|---|---|
| `OPENAI_API_KEY`, `OPENAI_MODEL` | none | Key and **chat model** for the symptom extraction. No default model on purpose: use one your account can use. |
| `EMBEDDING_MODEL` | empty | Empty keeps LangChain's default, which is what the index was built with. Change it only if the index was built with another model. |
| `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` | none, `evidgpt` | The index; namespaces `SYNDROMES_NAMESPACE` (`syndromes`) and `PRESCRIPTIONS_NAMESPACE` (`fangji`). |
| `SYNDROME_CANDIDATES`, `PRESCRIPTION_CANDIDATES`, `RERANK_TOP_N` | 30, 50, 5 | How many are retrieved, and how many are kept after reranking. |
| `COHERE_API_KEY`, `COHERE_RERANK_MODEL` | none | Key and **rerank model**. No default model on purpose. |
| `MONGODB_URI`, `MONGODB_DATABASE`, `MONGODB_COLLECTION`, `MONGODB_SEARCH_INDEX` | none, `cmedai`, `教科书`, `diseaseName` | Needs an Atlas Search autocomplete index on `病名`. |
| `API_KEY` | empty | When set, every endpoint except `/` and `/health` needs it as `X-API-Key`. **Set it before exposing the service**: each call costs money and sends the description to three providers. |
| `CORS_ORIGINS` | empty | Comma-separated allowed origins. No CORS headers when empty. |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | The server binds to localhost unless told otherwise (it used to bind to all interfaces). |

The old variable names (`OPENAI_API_KEY`, `PINECONE_API_KEY`, `COHERE_API_KEY`, `MONGODB_URI`, `PINECONE_INDEX_NAME`) still work.

## Project structure

```
src/fastkwan/
├── main.py         app factory (create_app), the `fastkwan` command
├── config.py       settings, and the error that becomes a 503
├── routes.py       the five endpoints
├── schemas.py      request and response models
├── security.py     the optional X-API-Key check
├── prompts.py      the symptom-extraction prompt (it was pasted twice before)
├── text.py         the 證型/症狀 reordering
└── services/       OpenAI NER, Pinecone + Cohere, MongoDB; built on first use
tests/              68 tests (every SDK is faked at its boundary)
Dockerfile  pyproject.toml  uv.lock  .env.example
```

## Testing

```bash
uv run pytest -q                           # 68 tests, 100% line coverage of src/fastkwan
uv run ruff check . && uv run ruff format --check .
```

The tests cover each endpoint's pipeline (what is searched, in which namespace, how many, what is reranked), the empty-symptom fallback, the no-result paths, input validation, the 401/502/503 paths (and that no upstream error text or key reaches the caller), CORS, the lazy construction of the clients, the settings, and that `.env.example` documents every setting.

## Deployment

```bash
docker build -t fastkwan .
docker run -p 8000:8000 --env-file .env fastkwan
```

The image runs as a non-root user, binds `0.0.0.0` inside the container and has a health check on `/health`.

## Versions

[VERSIONS.md](./VERSIONS.md). What changed and what needs your attention: [work-done.md](./work-done.md).

## License

MIT, see [LICENSE](./LICENSE).
