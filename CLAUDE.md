# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resume-Matcher parses resumes and job descriptions into structured data using Claude + Instructor, scores candidates via LLM-based recruiter evaluation, and generates match explanations. It ships as a Typer CLI and a FastAPI web app (browser UI + JSON API). Built with Python 3.10+, Pydantic v2, and the Anthropic API.

## Commands

```bash
# Install (editable mode, with dev dependencies: pytest, httpx)
pip install -e ".[dev]"

# Environment setup
cp .env.example .env   # then set ANTHROPIC_API_KEY (Windows: copy .env.example .env)

# Run tests (no API key needed, all tests use mocks)
pytest
pytest tests/test_schemas.py -v   # single file, verbose

# CLI commands (`resume-matcher` is the installed entry point; `python -m resume_matcher.cli` is equivalent)
resume-matcher extract-resume data/resumes/senior_backend.txt
resume-matcher extract-job data/jobs/senior_python_backend.txt
resume-matcher match data/resumes/senior_backend.txt data/jobs/senior_python_backend.txt
resume-matcher rank data/resumes/ data/jobs/senior_python_backend.txt

# Web app (http://127.0.0.1:8000, API docs at /docs)
uvicorn resume_matcher.web:app --host 127.0.0.1 --port 8000 --reload

# Web app via Docker (reads .env, mounts ./output)
docker compose up --build
```

## Architecture

The application is a pipeline: **Extract → Score → Explain**

All source code lives in `src/resume_matcher/`. There are two entry points: `cli.py` (Typer app) and `web.py` (FastAPI app).

### Pipeline flow

1. **extractor.py** — Sends raw resume/job text to Claude via Instructor. Claude returns structured data validated against Pydantic schemas (`Resume` or `JobDescription`). Instructor auto-retries up to 3 times if validation fails, feeding the error back to Claude for self-correction.

2. **scorer.py** — Takes the extracted structured data plus the original raw text, sends both to Claude with a recruiter-perspective system prompt. Returns a `MatchResult` with four component scores (required_skills, preferred_skills, experience, education), an overall score (holistic judgement, not a weighted average), matched/missing skills, an explanation, and a recommendation (strong_match/possible_match/weak_match). Scoring is LLM-based, so results are not deterministic.

3. **explainer.py** — Generates a natural language summary of the match. Uses the raw Anthropic client (not Instructor) since output is free-form text. Used by the web app's `/api/match` endpoint (overwrites `MatchResult.explanation`); the CLI does not call it and shows the scorer's explanation instead.

### Key modules

- **schemas.py** — All Pydantic v2 models: `Skill`, `WorkExperience`, `Education`, `Resume`, `JobDescription`, `ScoreBreakdown`, `MatchResult`. Contains field validators for graduation years, score ranges, experience values, and allowed recommendation values.
- **config.py** — Loads `.env` from the project root, validates `ANTHROPIC_API_KEY` (rejects dummy values), returns configured model name. Raises `ConfigError` on failure.
- **llm_client.py** — Single function `get_client()` returning an Instructor-wrapped Anthropic client.
- **cli.py** — Four Typer commands (`extract-resume`, `extract-job`, `match`, `rank`). Inputs are `.txt` files. All output JSON to the `output/` directory. Uses Rich for formatted console output.
- **web.py** — FastAPI app. Serves the UI at `/` (`templates/index.html`, `static/app.js`, `static/style.css`) and JSON endpoints: `GET /api/health`, `POST /api/extract-resume`, `/api/extract-job`, `/api/match`, `/api/rank`. POST endpoints take multipart form data — each input is an uploaded file or pasted text (file wins); `/api/rank` splits pasted resumes on `---`. The web app does not write to `output/`.

### LLM integration pattern

All LLM calls go through Instructor (`extractor.py`, `scorer.py`) except `explainer.py` which uses the raw Anthropic client. Instructor validates Claude's JSON output against Pydantic schemas and retries on validation failure. The configured model (default `claude-haiku-5-5`) is set via `CLAUDE_MODEL` in `.env`.

## Testing

Tests are in `tests/` and use `@patch` decorators to mock the Instructor client and config — no real API calls are made. Four test files cover schema validation (`test_schemas.py`), extraction (`test_extractor.py`), scoring (`test_scorer.py`), and the web API (`test_web.py`).

## Documentation

`README.md` is the user-facing setup and usage guide (from-scratch setup per OS, CLI, web app, Docker, API endpoints, troubleshooting). Keep it in sync when changing commands, endpoints, environment variables, or scoring behaviour.
