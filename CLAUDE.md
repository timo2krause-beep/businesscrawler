# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Modular SaaS platform for automated competitive intelligence, monitoring, and reporting. Python/FastAPI backend + Next.js frontend. German-language UI.

## Commands

```bash
# Backend (from project root, activate venv first)
source .venv/bin/activate
python -m uvicorn app:app --reload --port 8000

# Frontend (from /frontend)
cd frontend && npm run dev    # Port 3000

# Database (PostgreSQL via Docker, port 5433)
docker compose up -d          # Start DB container

# Test individual source
python -c "import asyncio; from core.sources.reddit_source import fetch_reddit_mentions; print(asyncio.run(fetch_reddit_mentions('Tesla', limit=3)))"
```

## Architecture

### Module System (`BaseModule` → `modules/`)
Every module inherits `BaseModule` (core/base_module.py) and implements the pipeline:
`fetch_data()` → `process_data()` → `generate_report()` → `run()`

Modules are registered in `app.py` via `registry.register()` and discovered by the API via `core/registry.py`.

**Current modules (8):** tech_stack_monitor, cve_monitor, rss_monitor, wettbewerbs_monitor, ki_wettbewerb, social_media_generator, social_sentiment, review_monitor

`social_media_generator` has no data source of its own — it reads the `competitor_profiles` cache
that `ki_wettbewerb` populates (via `core/competitor_store.py`) and turns it into ready-to-post
social media templates. Run `ki_wettbewerb` at least once first.

### Source System (`BaseSource` → `core/sources/`)
Data ingestion sources that return `list[NormalizedEvent]`. Used by modules internally.
Review sources are in `core/sources/reviews/` and return plain `list[dict]` instead of NormalizedEvents.

### Personalization Flow
User preferences (JSONB) → `api/module_router.py` creates fresh module instance per request with user-specific config → prevents global state mutation.

Key preference keys: `watched_repos`, `cve_keywords`, `rss_feeds`, `scraping_targets`, `ki_company_name`, `sentiment_company`, `review_company`

### Event Pipeline (`core/events.py` → `core/event_store.py`)
`NormalizedEvent` with SHA256-based `dedup_key` → `EventEngine` scores + deduplicates → stored in `normalized_events` table.

### AI Integration (`core/ai_service.py`)
OpenRouter client with `ai_chat()` and `ai_json()`. Used by ki_wettbewerb, social_sentiment, review_monitor modules.

### Web Scraping Change Detection
`core/sources/web_scraper.py` uses content hashing stored in `content_hashes` table. Diffs computed via `difflib`. Content text cached for diff computation.

### Competitor Caching (`core/competitor_store.py`)
KI-identified competitors cached in `competitor_profiles` table. Only refreshed when `needs_refresh=True` flag is set via trigger endpoint.

## Key Patterns

- **No global state mutation**: Always create new module instances per request (see module_router.py personalization block)
- **Graceful source failures**: Each data source can fail independently without blocking others
- **Preference types in frontend**: `pref_type` in `frontend/src/lib/modules.ts` controls UI: undefined=string list, "targets"=url+name+selector editor, "company"=single text input
- **Schema types for preferences**: `PreferenceSet.value` accepts `dict | list | str` (api/schemas.py)
- **DB sessions**: Use `get_db()` for FastAPI deps, `get_session()` context manager for standalone code

## Database

PostgreSQL on port 5433 (not default 5432). Connection: `postgresql://scraper:scraper@localhost:5433/scraper`

Models in `core/models.py`. Tables auto-created via `init_db()` on startup. Manual migrations via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.

## Config

All settings in `config/settings.py` via pydantic-settings, loaded from `.env`. Key vars: `DATABASE_URL`, `JWT_SECRET`, `OPENROUTER_API_KEY`, `STRIPE_SECRET_KEY`, `GITHUB_TOKEN`.
