# Work done: tcm-med-ai (FastKwan)

Branch: `chore/modernize` (local, not pushed). Date: 2026-11-01.

## What was there
Six tracked files: a 266-line `main.py` (a FastAPI app with three endpoints that call OpenAI, Pinecone, Cohere and MongoDB), a `requirements.txt`, a README, `.env.example`, `.gitignore`, `LICENSE`. No tests, no Dockerfile, no CI.

## Credentials in the git history (the most important part of this report)
The working tree holds no credentials, but **the history does**. Counting only (nothing was printed or tested): across 9 commits there are **10 lines with an OpenAI-key-shaped string** and **12 lines with a MongoDB connection string that includes a password** that do not look like placeholders, in `main.py`, `newmain.py`, `function_to_integrate.py`, `test.py`, `backup.py` and an earlier `.env.example` (all removed from the tree since). A pull request in 2025 ("Redact exposed API key in backup.py") came from someone who found a key in this repository, which suggests it is public.
- **Rotate the OpenAI key and the MongoDB database user's password** (and look at the Atlas network access list) if they were ever real. Redacting a file does not remove it from history.
- Removing them from history means rewriting it and force-pushing, which is a push you must do yourself.

## Bugs and risks found, and what was done
| Problem | Fix |
|---|---|
| `requirements.txt` listed 12 indirect dependencies and omitted `fastapi`, `uvicorn`, `openai`, `cohere`, `langchain-*`, `pymongo` and `python-dotenv`: a fresh install could not run the app. Its `pinecone==8.1.2` also conflicts with `langchain-pinecone` (the latest, 0.2.13, requires `pinecone<8`), so the two could not be installed together | `pyproject.toml` + `uv.lock` (Python 3.13, 87 packages) |
| Importing the module raised unless four API keys were set, and it connected to Pinecone and MongoDB at import (nothing could be imported or tested offline) | Settings from the environment; the clients are built on first use; an unconfigured endpoint answers 503 naming the variables |
| No access control: anyone who could reach the port could spend your OpenAI, Cohere and Pinecone quota and send text through them | Optional `API_KEY` (`X-API-Key`, constant-time comparison); documented as required before exposing the service |
| `uvicorn.run(app, host="0.0.0.0")` | Binds to 127.0.0.1 by default (`HOST`; the Docker image sets 0.0.0.0) |
| Every handler returned `str(error)` to the caller (provider messages, URLs, key fragments) | 502 with a fixed message; the details are logged |
| The 20-line symptom-extraction prompt and the whole NER, search and rerank pipeline were pasted into `/syndrome` and `/prescription` | One prompt module, one pipeline helper |
| `co.rerank` read `doc.document["text"]`, which the current Cohere v2 answer does not carry (only index and score) | The text is looked up by index; verified against the real v2 client |
| Models hard-coded (`gpt-3.5-turbo`, `rerank-multilingual-v2.0`) | `OPENAI_MODEL`, `COHERE_RERANK_MODEL` (no defaults) |
| An empty extraction result sent an empty query to the vector search | Falls back to the description itself |
| `query: str` without limits | 1 to 4000 characters, 422 otherwise |
| `LifestyleResponse` and `PrescriptionResponse` were defined but not used; `/lifestyle` had no response model | Used |
| The Mongo client was never closed except in a lifespan hook of a module-level client | Closed through the services object on shutdown |

Kept as it was: the three routes and their request body, the response shapes (`{"result": ...}`, the disease document with `病名` / `预防与调摄`, `{"results": [{text, index, relevance_score}]}`, and the empty-result messages), the Mongo Stable API v1 setting, the database, collection and index names, and the old variable names.

## Changes by file
| Path | Before | Change |
|---|---|---|
| `main.py` | 266 lines, everything | removed; split into `src/fastkwan/` (`main`, `config`, `routes`, `schemas`, `security`, `prompts`, `text`, `services/`) |
| `requirements.txt` | 12 pins | removed; `pyproject.toml`, `uv.lock`, `.python-version` |
| `README.md` | install with pip and `uvicorn main:app` | rewritten to match the code |
| `.env.example` | 5 variables | all 21 settings with demo values (a test keeps it in sync with `Settings`) |
| `.gitignore` | `.env` | adds `.env.*` with `!.env.example` |
| `tests/` | absent | 68 tests |
| `Dockerfile`, `.dockerignore`, `.github/workflows/ci.yml` | absent | non-root image with a health check; CI (lint, format, tests, image build) |
| `VERSIONS.md`, `work-done.md` | absent | written |
| `LICENSE` | MIT | unchanged |

## Verification (actual runs)
- `uv run pytest -q`: **68 passed**, 100% line coverage of `src/fastkwan`; `ruff check` and `ruff format --check` clean.
- Mutation checks (the defect put back, the suite must fail): wrong text taken from the rerank answer (1 test fails), API key never checked (3), upstream error text returned (5), no fallback for an empty extraction (1), prescriptions searched in the syndromes namespace (1), a missing setting reported as 502 (1), entries not reordered (3), `rerank_top_n` ignored (1), an eager client at construction (the suite cannot even be collected), a typo in `.env.example` (2). The first attempt at the eager-client mutant crashed on an unset attribute, so it proved nothing and was redone correctly.
- The real `openai` and Cohere v2 clients against a local fake HTTP server: parsing and request shape confirmed.
- The real server from an empty environment, and with `API_KEY`: see VERSIONS.md.
- The Docker image: builds, non-root, health check healthy, no tests or env files inside.
- A count-only secret scan of the working tree (only the placeholder in `.env.example`) and of the full history (see the first section).
- **Not verified:** any call to the real OpenAI, Pinecone, Cohere or Atlas (no live credentials were used), the availability of the old model names, a GitHub Actions run.

## Needs your attention
- **Rotate** the OpenAI key and the MongoDB credentials that appear in history (first section).
- Set `OPENAI_MODEL` and `COHERE_RERANK_MODEL` to models your accounts can use, and **set `API_KEY`** before exposing the service.
- The embedding model is left to LangChain's default because the index was built with it; if the index was built with another model, set `EMBEDDING_MODEL`.
- `uv run fastkwan` replaces `uvicorn main:app --reload`; for reload use `uv run uvicorn fastkwan.main:app --reload`.
- Nothing pushed. To publish: `git push -u origin chore/modernize`
