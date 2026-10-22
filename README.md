# Resume-to-Job Matcher

Parses resumes and job descriptions into structured data with Claude + [Instructor](https://github.com/jxnl/instructor), evaluates each candidate the way a senior technical recruiter would, and ranks candidates against a job.

You can use it two ways:

- **CLI** — run commands against `.txt` files; results are printed and saved as JSON in `output/`.
- **Web app** — a FastAPI server with a browser UI and a JSON API for uploading or pasting resumes and job descriptions.

## Prerequisites

| Requirement | Notes |
|---|---|
| Python **3.10 or newer** | Check with `python --version` (or `python3 --version` on macOS/Linux). Download from [python.org](https://www.python.org/downloads/). |
| Git | To clone the repository. |
| Anthropic API key | Create one at [console.anthropic.com](https://console.anthropic.com/). Required for extraction, matching, and ranking (not for running tests). |
| Docker *(optional)* | Only if you want to run the web app in a container instead of installing Python. |

## Setup from scratch

### 1. Get the code

```bash
git clone <repository-url> Resume-Matcher
cd Resume-Matcher
```

### 2. Create and activate a virtual environment

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If PowerShell refuses to run the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

**Windows (Command Prompt)**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

Your prompt should now start with `(.venv)`. Activate the environment again in every new terminal you use for this project.

### 3. Install the package

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This installs the app and its dependencies in editable mode, plus the dev tools (`pytest`, `httpx`) needed for the test suite. Use `pip install -e .` if you don't need the tests.

### 4. Configure your API key

Copy the example environment file:

```bash
# macOS / Linux
cp .env.example .env
```

```powershell
# Windows (PowerShell or Command Prompt)
copy .env.example .env
```

Then open `.env` and set your key:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-haiku-5-5
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Your Anthropic API key. The app refuses to run while it's empty or still the placeholder `your-api-key-here`. |
| `CLAUDE_MODEL` | No | `claude-haiku-5-5` | Claude model used for extraction, scoring, and explanations. |

The `.env` file must be in the project root (next to `pyproject.toml`). It is git-ignored, so your key won't be committed.

### 5. Verify the install

```bash
pytest
```

All tests use mocks, so they pass without an API key and make no network calls.

## Running the CLI

Sample resumes are in `data/resumes/` and sample job descriptions in `data/jobs/`. Input files must be plain `.txt`.

Run from the project root with the virtual environment activated. The installed `resume-matcher` command and `python -m resume_matcher.cli` are interchangeable.

### Extract a resume

```bash
resume-matcher extract-resume data/resumes/senior_backend.txt
```

Saves `output/resume_<name>.json`.

### Extract a job description

```bash
resume-matcher extract-job data/jobs/senior_python_backend.txt
```

Saves `output/job_<name>.json`.

### Match one resume against a job

```bash
resume-matcher match data/resumes/senior_backend.txt data/jobs/senior_python_backend.txt
```

Prints a score breakdown and saves `output/match_<resume>_vs_<job>.json`.

### Rank every resume in a folder against a job

```bash
resume-matcher rank data/resumes/ data/jobs/senior_python_backend.txt
```

Scores every `.txt` file in the folder, prints a leaderboard sorted by overall score, and saves `output/rank_vs_<job>.json`.

Run `resume-matcher --help` or `resume-matcher <command> --help` for details. The `output/` directory is created automatically.

## Running the web app

### Locally

```bash
uvicorn resume_matcher.web:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000> in your browser. `--reload` restarts the server when code changes; omit it outside development. Stop the server with `Ctrl+C`.

If port 8000 is already in use, pick another one with `--port 8001`.

### With Docker

Make sure `.env` exists with your API key (step 4 above), then:

```bash
docker compose up --build
```

Open <http://localhost:8000>. Stop with `Ctrl+C`, or run `docker compose down` from another terminal. The container reads `.env` for its configuration and mounts `./output` into the container.

### API endpoints

All `POST` endpoints accept `multipart/form-data`. Each input can be uploaded as a file or pasted as text; if both are given, the file wins.

| Method | Path | Form fields | Returns |
|---|---|---|---|
| `GET` | `/` | — | Web UI |
| `GET` | `/api/health` | — | `{"status": "ok", "api_key_configured": true/false}` |
| `POST` | `/api/extract-resume` | `file` or `text` | Structured resume |
| `POST` | `/api/extract-job` | `file` or `text` | Structured job description |
| `POST` | `/api/match` | `resume_file` or `resume_text`, `job_file` or `job_text` | Match result with a generated explanation |
| `POST` | `/api/rank` | `resume_files` (multiple) or `resume_texts`, `job_file` or `job_text` | Match results sorted by overall score |

For `/api/rank`, separate multiple pasted resumes in `resume_texts` with a line containing `---`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/match \
  -F "resume_file=@data/resumes/senior_backend.txt" \
  -F "job_file=@data/jobs/senior_python_backend.txt"
```

Interactive API docs are available at <http://127.0.0.1:8000/docs> while the server is running.

## How it works

The pipeline is **Extract → Score → Explain**.

1. **Extract** (`extractor.py`) — Claude turns raw resume and job text into structured data validated against Pydantic models (`Resume`, `JobDescription`).
2. **Score** (`scorer.py`) — Claude acts as a senior technical recruiter. It receives both the raw text and the structured data and returns a `MatchResult`.
3. **Explain** (`explainer.py`) — Claude writes a plain-language summary of the match. The web app's `/api/match` endpoint uses this; the CLI shows the explanation produced during scoring.

### Scoring

Scoring is **LLM-based**, not a fixed formula. Claude rates four components from 0 to 100:

| Component | What Claude considers |
|---|---|
| Required skills | Equivalent or related technologies (e.g. Flask ≈ FastAPI), transferable skills, and depth of experience — not just keyword matches. |
| Preferred skills | The same, for nice-to-have qualifications. |
| Experience | Relevance of past roles, leadership, project complexity, and career progression — not just years. |
| Education | Degree relevance, certifications, and continuous learning. Strong bootcamp graduates can score well when a degree isn't strictly required. |

The **overall score** (0–100) is Claude's holistic judgement rather than an average. It weighs required skills and experience most heavily.

Each result also includes matched skills, missing skills, a short recruiter summary, and one of these recommendations:

- **strong_match** — would advance the candidate to interview
- **possible_match** — notable gaps, but worth considering
- **weak_match** — significant gaps, unlikely to be a good fit

Because scores come from an LLM, the same inputs can produce slightly different scores across runs.

### Instructor retries

Extraction and scoring go through [Instructor](https://github.com/jxnl/instructor), which validates Claude's JSON output against the Pydantic schemas. If validation fails (for example, an out-of-range graduation year or a negative years-of-experience value), Instructor sends the validation error back to Claude and retries, up to `max_retries=3` times. Claude can correct its own output without manual intervention.

## Project structure

```
src/resume_matcher/
  schemas.py      # Pydantic v2 models (Resume, JobDescription, MatchResult, ...)
  config.py       # .env loading and API key validation
  llm_client.py   # Instructor-wrapped Anthropic client
  extractor.py    # LLM-powered resume and job description parsing
  scorer.py       # LLM-based recruiter scoring
  explainer.py    # LLM-generated match explanations
  cli.py          # Typer CLI commands
  web.py          # FastAPI web app and JSON API
  templates/      # HTML template for the web UI
  static/         # CSS and JavaScript for the web UI
data/
  resumes/        # Sample resume .txt files
  jobs/           # Sample job description .txt files
tests/            # Unit tests (mocked; no API key needed)
output/           # JSON results written by the CLI (created on first run)
Dockerfile
docker-compose.yml
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Configuration error: ANTHROPIC_API_KEY is not set...` | Create `.env` in the project root and set a real key (see step 4). |
| `ModuleNotFoundError: No module named 'resume_matcher'` | Activate the virtual environment and run `pip install -e .` from the project root. |
| `resume-matcher: command not found` / not recognized | The virtual environment isn't active. Activate it, or use `python -m resume_matcher.cli` instead. |
| `pytest: command not found` | Install dev dependencies: `pip install -e ".[dev]"`. |
| `python` not found on macOS/Linux | Use `python3` instead. |
| Address already in use on port 8000 | Stop the other process, or start uvicorn with `--port 8001` (for Docker, change the host port in `docker-compose.yml`, e.g. `"8001:8000"`). |
| `API error: ...` (authentication, rate limit, model not found) | Check that the API key is valid and has credit, and that `CLAUDE_MODEL` names a model your account can use. |
