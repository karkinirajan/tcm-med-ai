# Versions

Read from `uv.lock` and the installed packages on 2026-11-01.

| Component | Version | Was | Where it is set |
|---|---|---|---|
| Python | 3.13 (image `python:3.13-slim-trixie`; 3.13.18 locally) | "3.10 or higher" in the README | `.python-version`, `pyproject.toml`, `Dockerfile` |
| FastAPI | 0.162.0 | "0.115+" in the README, not in `requirements.txt` | `pyproject.toml` (`>=0.115`) |
| uvicorn | 0.54.0 | not in `requirements.txt` | |
| pydantic / pydantic-settings | 2.14.2 / 2.16.2 | not in `requirements.txt` | |
| openai | 3.42.0 | not in `requirements.txt` | |
| cohere | 7.3.0 (the v2 client) | not in `requirements.txt` (the old code used the v1 client) | |
| pinecone | 7.3.0 | 8.1.2 in `requirements.txt` | held below 8 by `langchain-pinecone` 0.2.13 (latest), which requires `pinecone<8`; the old pin could not be installed next to it |
| langchain-openai / langchain-pinecone | 1.7.3 / 0.2.13 | not in `requirements.txt` | |
| pymongo | 4.19.0 | not in `requirements.txt` | |
| pytest / pytest-cov / httpx / ruff (dev) | 9.2.0 / 7.1.0 / 0.28.1 / 0.17.3 | absent | |
| uv (in the image) | 0.13.6 | | `Dockerfile` |

87 packages are locked. The old `requirements.txt` pinned 12, **all of them indirect dependencies** except `pinecone`: `fastapi`, `uvicorn`, `openai`, `cohere`, `langchain-openai`, `langchain-pinecone`, `pymongo` and `python-dotenv`, which `main.py` imports, were missing, so a fresh `pip install -r requirements.txt` could not run the app.

No model names are pinned. The old code hard-coded `gpt-3.5-turbo` and `rerank-multilingual-v2.0`; both are settings now (`OPENAI_MODEL`, `COHERE_RERANK_MODEL`) because which models an account can use is not something that could be verified here.

## Verified here

- 68 tests pass, 100% line coverage of `src/fastkwan`; `ruff check` and `ruff format --check` are clean.
- The real `openai` and Cohere v2 clients, pointed at a local fake HTTP server, parse a chat answer and a rerank answer of the documented shape and send the expected requests (model, query, documents, `top_n`, bearer key).
- The real server (`uv run fastkwan`) started from an empty environment: `/health` 200, the other endpoints 503 with the missing names, an empty query 422, bound to 127.0.0.1; with `API_KEY` set, 401 without the key and 503 with it.
- The Docker image builds (910 MB), runs as `appuser`, its health check turns healthy, and it contains no tests or env files.

## Not verified here

- Any call to the real OpenAI, Pinecone, Cohere or MongoDB Atlas (no live credentials were used): the Pinecone and Atlas Search parts are tested against fakes of the calls the code makes, so the index layout (`text` metadata key, namespaces) and the Atlas Search index (`diseaseName` on `病名`) are as the old code assumed.
- Whether `gpt-3.5-turbo`, `rerank-multilingual-v2.0` or the default embedding model are still available to an account: set the models in the environment.
- A GitHub Actions run.
