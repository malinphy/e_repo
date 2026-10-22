# Copilot Instructions

## Repository state

The backend is implemented; the frontend does not exist yet. The working tree contains:

- `backend/` — the FastAPI + LangGraph e-commerce search agent (see **Backend** below)
- `requirements.txt` — pinned Python dependencies (**always keep in sync**)
- `pytest.ini` — pytest config for the backend suite
- `.env` — local secrets (API keys for Gemini, OpenAI, HuggingFace, Groq, Fireworks, DeepSeek, Tavily, SerpAPI, SEC; PostgreSQL credentials for an `EXPEDIA_SEARCH` database)
- `.vscode/mcp.json` — registers the **Docs by LangChain** MCP server (`https://docs.langchain.com/mcp`)
- `.gitignore` — Python-flavored ignore list with many project-specific exclusions (see below)
- `venv/` — local virtual environment (not tracked)

There is still no `README.md`, no `pyproject.toml`, no frontend, no linter/formatter config, and no CI configuration.

## Project direction

This is an **agentic e-commerce bot**. The repository contains both a **backend** and (eventually) a **frontend** folder. The backend uses LangGraph over LangChain, and is designed to integrate with multiple LLM providers (keys for OpenAI, Gemini, Groq, Fireworks, DeepSeek are present in `.env`; only OpenAI is wired up so far).

## Conventions

### Secrets and environment

- All API keys and DB credentials live in `.env` at the repo root. The file is gitignored — never commit it, and never hard-code these values in source.
- The `.env` defines two parallel sets of Postgres variables (`DB_*` and `PG_*`) pointing at the same `EXPEDIA_SEARCH` database on `localhost:5432`. When writing DB code, pick one naming convention per module and stay consistent.
- `FLIGHT_USER_ID = "1234"` is present — flight-search tooling is part of the planned scope.

### `.gitignore` patterns to respect

The ignore list is opinionated. Do not commit anything matching these patterns (they are explicitly excluded by the project owner):

- `db/flights_agent.db`, `db/databases/flights_agent.db`, `database/data/flights_agent.db` — local SQLite/agent DBs
- `fe/guidences/ui_guidelines.md`, `fe/guidences/ux_guidelines.md` — frontend guidance notes
- `*htmls`, `*data`, `*prompts`, `*utils`, `*vectorizer` — broad scratch/exploration directories
- `*fe_agent_test`, `*local_tests_variations`, `*spectrum_test`, `*lm_studio_test`, `*local-llm-judge`, `*llm_judge`, `*llama.cpp` — experimental test harnesses
- `CODEBASE.md`, `analiz_c.md`, `api_dokumantasyon.md`, `obeservation.py`, `lm_studio.py`, `test_lm.py`, `flight_result.json` — ad-hoc analysis/script files
- `*deneme.ipynb` — exploratory notebooks

If you create files matching these patterns, expect them to be ignored. Use descriptive, project-specific names instead.

### MCP tooling

- The **Docs by LangChain** MCP server is preconfigured in `.vscode/mcp.json`. Use it for any LangChain API/feature questions before guessing — it returns authoritative, current docs.
- **Before adding or upgrading any library, check the available MCP servers first** (e.g. Docs by LangChain, package registries, framework docs). MCP-provided docs are the source of truth over training-data guesses.

### Skills

- Before starting non-trivial work, check the available **skill files** (e.g. `python-fact-grounded-coding`, `python-add-type-annotations`, `pylance-refactoring`, `python-write-stubs`, `add-python-version-support`, `drop-python-version-support`, `address-pr-comments`, `create-pull-request`, `agent-customization`, `pylance-python-profiling`, `pylance-docs`, `python-type-inference`, `form-github-search-query`, `show-github-search-result`, `suggest-fix-issue`, `summarize-github-issue-pr-notification`, `troubleshoot`). Invoke the matching skill as the first action when one applies — do not just announce it.

### Branching

- Active development branch is `feat/test` (currently checked out). `main` exists on the remote. Open work against `feat/test` unless told otherwise.

### Project layout

- The repository will have a **backend** folder and a **frontend** folder. Place backend code (Python agents, APIs, DB access) under `backend/` and frontend code under `frontend/`. Do not mix the two.

### Dependency management

- All Python dependencies must be tracked in `requirements.txt` at the repo root.
- **Every library entry must include an exact version pin** (e.g. `langchain==0.3.7`, not `langchain>=0.3`).
- When you install a new library, **update `requirements.txt` in the same change** — add the package with its pinned version. If `requirements.txt` does not exist yet, create it.
- When you upgrade or change a library version, update the corresponding line in `requirements.txt` to reflect the new pinned version.
- Do not leave unpinned, loosely-pinned (`>=`, `~=`), or commented-out dependencies in `requirements.txt`.

### Design patterns

- Code must be written to be **reusable**. Prefer established design patterns over ad-hoc structure.
- **Choose the pattern that fits the problem** — do not force a pattern. Common fits in this project:
  - **Strategy** — for swappable LLM providers, prompt templates, or tool implementations (the agent will integrate with multiple providers — OpenAI, Gemini, Groq, Fireworks, DeepSeek).
  - **Factory** — for constructing agents, tools, or DB clients from configuration.
  - **Repository** — for data access over the SQLite agent DB (see `backend/ecommerce_agent/repositories/`) and any flight/product stores.
  - **Adapter** — for wrapping third-party APIs (SerpAPI, Tavily, SEC, HuggingFace) behind a project-internal interface.
  - **Chain of Responsibility / Pipeline** — for the agent's tool-calling / reasoning steps.
  - **Observer / Event bus** — for decoupled agent ↔ frontend communication if needed.
  - **Singleton** — only for genuinely single-instance resources (config loader, DB connection pool). Avoid otherwise.
- New shared abstractions go under `backend/ecommerce_agent/common/` (or a clearly named subfolder) so they can be reused across modules. Do not duplicate logic across agents/tools.

## Backend (implemented)

Stack: **FastAPI + LangGraph + SQLAlchemy/SQLite + SerpAPI**. All code is in English.

```
backend/
  main.py                      # ASGI entrypoint (exposes `app`)
  data/                        # local SQLite files (gitignored)
  ecommerce_agent/
    common/config.py           # Settings (pydantic-settings) + get_settings() Singleton
    common/logging_setup.py    # configure_logging() for package loggers
    common/redaction.py        # redact() — strips secrets/URLs/tokens before logging
    common/llm/                # Strategy (LLMProvider ABC) + Factory (build_llm_provider)
    common/db/                 # Singleton engine, Base, init_db()
    models/                    # SQLAlchemy ORM tables (agent_runs, engine_results, search_history, …)
    repositories/              # Repository pattern (one class per model, takes a Session)
    tools/serpapi/             # Adapter (per engine) + Factory + LangChain tool wrappers
    services/                  # EngineSearchService — Facade over the adapters (shared by graph + API)
    schemas/                   # Pydantic request/response + ParsedQuery
    agent/                     # state, deps (DI container), graph, runner, nodes/
    api/                       # routers, app factory, request/response schemas
  tests/                       # pytest suite
```

### Commands

Run from the repo root with the local venv (`venv\Scripts\python.exe`).

| Task | Command |
| --- | --- |
| Run the API (dev, auto-reload) | `venv\Scripts\python.exe -m uvicorn main:app --reload --app-dir backend` |
| Run the API (no reload) | `venv\Scripts\python.exe backend\main.py` |
| Run all tests | `venv\Scripts\python.exe -m pytest` |
| Run one test file | `venv\Scripts\python.exe -m pytest backend/tests/test_api.py` |
| Run one test | `venv\Scripts\python.exe -m pytest backend/tests/test_api.py::test_health_reports_engines` |

- The server binds `API_HOST` / `API_PORT` from `.env` (defaults `127.0.0.1:8000`).
- Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`.
- Test config lives in `pytest.ini` (`pythonpath = backend`, `testpaths = backend/tests`), so no `PYTHONPATH` juggling is needed.
- Running a Python file from inside `backend/` (e.g. `python -c "from ecommerce_agent..."`) needs that directory as cwd, because `ecommerce_agent` resolves from `backend/`.
- There is **no linter/formatter configured yet**. If one is added, record its command here.

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | status, version, available engines |
| GET | `/engines` | names accepted by the per-engine endpoints |
| GET | `/engines/{engine}` | **free** read: what that marketplace returned for the last run (`?run_id=` to pin one) |
| GET | `/amazon` `/ebay` `/google_shopping` `/walmart` | **flat aliases** of `/engines/{engine}` — one fixed URL per marketplace for the frontend |
| POST | `/engines/{engine}/search` | **raw** results from one marketplace (no LLM, no persistence) |
| POST | `/engines/search` | raw results from several engines in one call (`engines` omitted ⇒ all) |
| POST | `/search` | full agent run (`run_id`, `engines`, `answer`, `products`, `results`, `engine_errors`) |
| POST | `/chat` | same pipeline, chat-shaped response (`run_id`, `query`, `answer`, `products`, `results`, `engine_errors`) |
| GET | `/search/history?user_id=<id>` | recent searches for a user |
| GET | `/runs/{run_id}` | persisted run record (`completed` / `failed`) |
| GET | `/runs/{run_id}/engines` | per-marketplace summary of that run (counts + errors) |
| GET | `/runs/{run_id}/engines/{engine}` | **exactly** what one marketplace returned in that run |

**Two ways to read per-marketplace results — pick the cheap one.** `GET /amazon`, `/ebay`,
`/google_shopping`, `/walmart` (and their `/engines/{engine}` aliases) plus the `/runs/{run_id}/engines*` routes
are read-only projections of data the `persist` node already stored: no query parameter that triggers a fetch, no
credits, no LLM. `GET /amazon` resolves the newest `engine_calls` row for that engine (or the row of an explicit
`?run_id=`) and returns `run_id`, `query`, `result_count`, `error`, `created_at` and `products`, so a client that
just called `POST /chat` can fan out to one fixed URL per marketplace. It answers 404 before any run exists and 404
for an engine that never produced a row. `POST /engines/*` is the only group that *spends* SerpAPI credits.

The `POST /engines/*` routes are the "split" view of the backend: they expose exactly what each SerpAPI adapter
returns, normalized to the shared product contract and stamped with `engine`. They deliberately skip the LLM and
skip run/history persistence, so they are the cheapest way to test a marketplace. An upstream SerpAPI failure is
returned as HTTP 200 with the refusal in `error`/`errors` (already `redact()`ed) so a client can degrade per
marketplace; an unknown engine name is HTTP 404. Each call still costs **one SerpAPI credit per engine**.

The `/runs/{run_id}/engines*` routes are the **after-the-fact** view of a real agent run: the `persist` node writes
one `engine_calls` row per engine (count + optional `error`) and one `engine_products` row per product, so the
frontend can fetch "what did walmart return for run 42" without re-querying SerpAPI (no credits, no LLM). A failed
engine still gets a row, which is why the endpoint can distinguish "no matches" from "marketplace unavailable".
`EngineResultsRepository.replace_for_run()` deletes then re-inserts for the run, so a re-executed `persist` node
overwrites instead of duplicating. These tables are created by `create_all`, which does **not** migrate an existing
SQLite file — delete `backend/data/*.db` if a model column changes.

### Manual smoke test

With the server running:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/engines" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/engines/walmart/search" -Method POST `
  -ContentType "application/json" -Body '{"query":"usb c hub","num":5}' -UseBasicParsing
# one paid call, then read every marketplace for free:
Invoke-WebRequest -Uri "http://127.0.0.1:8000/chat" -Method POST -ContentType "application/json" `
  -Body '{"message":"nike ayakkabi","user_id":"demo"}' -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/amazon" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/ebay" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/google_shopping" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/walmart" -UseBasicParsing
# pin an older run: /amazon?run_id=<run_id>
Invoke-WebRequest -Uri "http://127.0.0.1:8000/runs/<run_id>/engines" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/runs/<run_id>/engines/walmart" -UseBasicParsing
```

`POST /chat` and `POST /search` cost real credits (1 LLM call + 1 SerpAPI call per engine) and `POST /engines/*`
costs 1 SerpAPI call per engine, so prefer the pytest suite while iterating. Every `GET` above is database-only.

### SerpAPI adapters (learned the hard way)

Each engine is an **Adapter + Template Method**: the subclass declares `engine` + `query_param` and implements `normalize(raw)`; `SerpAPIEngineAdapter.search()` builds the request from those two attributes. Adding an engine means adding one class and one `ENGINE_CLASSES` entry — never a branch in the client, in `execute_tools`, or in the API routes.

**Every engine names its query parameter differently.** Sending `q` to all of them returns HTTP 400 `Missing query ... parameter.`:

| Engine | Query param | Result container | Price shape | Link field |
| --- | --- | --- | --- | --- |
| `google_shopping` | `q` | `shopping_results[]` | `price` (str) | `link` |
| `amazon` | `k` (or `node`) | `organic_results[]` | `price` (str) + `extracted_price` (float) | `link` / `link_clean` |
| `ebay` | `_nkw` | `organic_results[]` | `price: {raw, extracted}` — no rating/reviews | `link` |
| `walmart` | `query` (or `cat_id`) | `organic_results[]` | `primary_offer.offer_price` — no top-level `price` | `product_page_url` |

- `num` is accepted by every engine.
- `normalize()` must return **exactly** `{title, price, source, link, rating, reviews}` for every product (`_spread()` enforces this). `synthesize._extract_price()` cannot parse dicts, so prices are flattened during normalization, not during ranking.
- When a payload looks wrong, probe the live response before guessing at a shape; do not infer field names from a sibling engine.

### Secrets and logging

- **Never log a raw exception from an HTTP client.** `httpx.HTTPStatusError.__str__` embeds the full request URL, which carries `api_key`; the same applies to `requests` and most provider SDKs. Raise a project error that excludes the URL (see `SerpAPIError`) and pass anything provider-supplied — status details, error bodies — through `common.redaction.redact()` first.
- `redact()` masks every configured secret (≥8 chars, longest first), `api_key=...` query fragments, and `sk-…` / 40-hex-char tokens. Route any user-facing or persisted error text through it.
- Only `mask_secret()` (`***e56a`) may appear in logs. If a new secret is added to `Settings`, add it to `redaction._configured_secrets()` too.
- A provider key that leaks once is compromised: tell the user to rotate it.

### Testing conventions

- Inject `AgentDeps(engines=..., llm_factory=..., session_factory=...)` — never build real SerpAPI clients or real LLMs in tests.
- `llm_factory=lambda: None` disables the LLM entirely; nodes then take their deterministic heuristic/fallback path. This is the primary seam for testing non-deterministic behavior.
- Use `FakeAdapter` / `FakeLLM` from `backend/tests/conftest.py`; use the `session_factory` fixture (in-memory SQLite with `StaticPool`) for DB-backed tests.
- `create_app(agent_deps=...)` accepts injected dependencies so API tests can run against fakes via `TestClient`.

### Runtime conventions

- `SERPAPI_API_KEY` comes from `.env`; the app still starts without it (engines just return no products).
- The graph is a linear pipeline: `parse_query → plan_tools → execute_tools → synthesize → persist`. Every node degrades gracefully — an LLM failure falls back to heuristics, a single failing engine is isolated, and a persistence failure never breaks the response. Preserve this behavior when adding nodes.
- `state["error"]` is set only when **zero** products were collected across all engines.
- SQLite access is fully synchronous SQLAlchemy; sync FastAPI endpoints run in the threadpool.

### Troubleshooting

- **`.env` changes require a restart.** `Settings` is loaded once and `get_settings()` is `@lru_cache`d, so an already-running server keeps the old values. Uvicorn `--reload` only watches `*.py`; add `--reload-include *.env` to also restart on `.env` edits.
- **`.env` wins over the shell environment.** `config.py` runs `load_dotenv(..., override=True)` at import time, so a stale `OPENAI_API_KEY` exported in the shell or set as a Windows user variable cannot shadow the file. Whenever that happens the app logs
  `environment variables overridden by <repo>\.env: OPENAI_API_KEY`, and the startup line ends with `overridden_env=['OPENAI_API_KEY']`.
  Set `DOTENV_OVERRIDE=0` to restore normal precedence (`os.environ` wins) — do this in CI or containers where real environment variables are authoritative.
- **Check which secrets the server actually loaded.** On startup the app logs one line:
  `config: llm_provider=openai openai_key=***qQAA (len=164) serpapi_key=***e56a (len=64) engines=4 overridden_env=none`.
  Compare the tail/length against `.env` to confirm the expected value was picked up. Secrets are never logged in full — use `mask_secret()` for any new one.
- **`[Errno 10048] ... bind` on startup** means another process already owns the port. Find it with
  `Get-NetTCPConnection -LocalPort 8000 -State Listen` and stop it, or start on another port with `$env:API_PORT="8011"`.
  A stale server also keeps `backend/data/ecommerce_agent.db` locked and serves the *old* config, which looks like "my key was not overridden".
- **Package logs are silent by default.** Uvicorn configures only its own loggers; `configure_logging()` in `backend/main.py` wires the `ecommerce_agent` logger. When running via `uvicorn main:app`, call it too or use `--log-level info` plus your own handler.

