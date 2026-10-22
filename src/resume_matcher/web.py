"""FastAPI web application for Resume-Matcher."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from resume_matcher.config import ConfigError, get_api_key
from resume_matcher.extractor import extract_job, extract_resume
from resume_matcher.explainer import generate_explanation
from resume_matcher.scorer import score_match

logger = logging.getLogger(__name__)

_here = Path(__file__).resolve().parent
app = FastAPI(title="Resume Matcher", version="0.1.0")
app.mount("/static", StaticFiles(directory=_here / "static"), name="static")
templates = Jinja2Templates(directory=_here / "templates")


async def _resolve_input(
    file: Optional[UploadFile] = None,
    text: Optional[str] = None,
    label: str = "input",
) -> str:
    """Return text content from an uploaded file or pasted text.

    File takes priority if both are provided.
    """
    if file and file.size:
        content = await file.read()
        return content.decode("utf-8", errors="replace")
    if text and text.strip():
        return text.strip()
    raise HTTPException(status_code=400, detail=f"No {label} provided. Upload a file or paste text.")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/health")
async def health():
    try:
        get_api_key()
        return {"status": "ok", "api_key_configured": True}
    except ConfigError:
        return {"status": "ok", "api_key_configured": False}


@app.post("/api/extract-resume")
async def api_extract_resume(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    content = await _resolve_input(file, text, "resume")
    try:
        resume = extract_resume(content)
        return resume.model_dump()
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Resume extraction failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@app.post("/api/extract-job")
async def api_extract_job(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    content = await _resolve_input(file, text, "job description")
    try:
        job = extract_job(content)
        return job.model_dump()
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Job extraction failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@app.post("/api/match")
async def api_match(
    resume_file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    job_file: Optional[UploadFile] = File(None),
    job_text: Optional[str] = Form(None),
):
    r_text = await _resolve_input(resume_file, resume_text, "resume")
    j_text = await _resolve_input(job_file, job_text, "job description")
    try:
        resume = extract_resume(r_text)
        job = extract_job(j_text)
        result = score_match(resume, job, r_text, j_text)
        explanation = generate_explanation(resume, job, result)
        result.explanation = explanation
        return result.model_dump()
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Match failed")
        raise HTTPException(status_code=500, detail=f"Match failed: {e}")


@app.post("/api/rank")
async def api_rank(
    resume_files: Optional[list[UploadFile]] = File(None),
    resume_texts: Optional[str] = Form(None),
    job_file: Optional[UploadFile] = File(None),
    job_text: Optional[str] = Form(None),
):
    j_text = await _resolve_input(job_file, job_text, "job description")

    # Collect resume texts from uploaded files or split pasted text by separator
    resume_contents: list[str] = []
    if resume_files:
        for f in resume_files:
            if f.size:
                raw = await f.read()
                resume_contents.append(raw.decode("utf-8", errors="replace"))
    if not resume_contents and resume_texts and resume_texts.strip():
        # Split multiple pasted resumes by "---" separator
        parts = [p.strip() for p in resume_texts.split("---") if p.strip()]
        resume_contents.extend(parts)
    if not resume_contents:
        raise HTTPException(status_code=400, detail="No resumes provided.")

    try:
        job = extract_job(j_text)
        results = []
        for r_text in resume_contents:
            resume = extract_resume(r_text)
            result = score_match(resume, job, r_text, j_text)
            results.append(result.model_dump())
        results.sort(key=lambda r: r["overall_score"], reverse=True)
        return results
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Ranking failed")
        raise HTTPException(status_code=500, detail=f"Ranking failed: {e}")
