# Copilot Instructions

## Repository state

This repository is currently a scaffold. The working tree contains only:

- `.env` — local secrets (API keys for Gemini, OpenAI, HuggingFace, Groq, Fireworks, DeepSeek, Tavily, SerpAPI, SEC; PostgreSQL credentials for an `EXPEDIA_SEARCH` database)
- `.vscode/mcp.json` — registers the **Docs by LangChain** MCP server (`https://docs.langchain.com/mcp`)
- `.gitignore` — Python-flavored ignore list with many project-specific exclusions (see below)
- `venv/` — local virtual environment (not tracked)

There is no source code, no `README.md`, no `CONTRIBUTING.md`, no `requirements.txt` / `pyproject.toml`, no test suite, and no CI configuration yet. Build/test/lint commands will need to be added once the project is bootstrapped.

## Project direction

This is an **agentic e-commerce bot**. The repository will contain both a **backend** and a **frontend** folder. The agent will likely use LangChain (the MCP server is configured for LangChain docs) and integrate with multiple LLM providers (keys for OpenAI, Gemini, Groq, Fireworks, DeepSeek are present in `.env`).

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
  - **Repository** — for data access over the `EXPEDIA_SEARCH` Postgres DB and any flight/product stores.
  - **Adapter** — for wrapping third-party APIs (SerpAPI, Tavily, SEC, HuggingFace) behind a project-internal interface.
  - **Chain of Responsibility / Pipeline** — for the agent's tool-calling / reasoning steps.
  - **Observer / Event bus** — for decoupled agent ↔ frontend communication if needed.
  - **Singleton** — only for genuinely single-instance resources (config loader, DB connection pool). Avoid otherwise.
- New shared abstractions go under `backend/common/` (or a clearly named subfolder) so they can be reused across modules. Do not duplicate logic across agents/tools.

## What is NOT yet defined

The following are absent and should be established before relying on them in suggestions:

- Build / test / lint commands (no `Makefile`, `package.json`, `pyproject.toml`, or CI workflow)
- Test framework and how to run a single test
- Concrete contents of `backend/` and `frontend/` (folders do not exist yet)
- Coding style / formatter config

When these are added, update this file with the concrete commands.
