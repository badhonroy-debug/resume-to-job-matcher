"""LLM-based scoring of resume-to-job matches using Instructor."""

import logging

from resume_matcher.config import get_model
from resume_matcher.llm_client import get_client
from resume_matcher.schemas import (
    JobDescription,
    MatchResult,
    Resume,
)

logger = logging.getLogger(__name__)

SCORER_SYSTEM_PROMPT = """\
You are a senior technical recruiter evaluating a candidate's resume against a job description.

You will receive BOTH the raw text (for presentation/context quality) and structured data (for factual accuracy). Use both to produce a holistic evaluation.

Score each dimension 0-100 from a recruiter's perspective:

**Required Skills (0-100):**
Not just keyword matching — consider equivalent/related technologies (e.g. Flask ≈ FastAPI, AWS ≈ GCP), transferable skills, and depth of experience with each skill as evidenced by the resume.

**Preferred Skills (0-100):**
Same nuanced evaluation as required skills, but for nice-to-have qualifications.

**Experience (0-100):**
Quality over quantity — relevance of past roles to this position, leadership experience, project complexity, career progression. Don't just compare year counts.

**Education (0-100):**
Degree relevance to the role, certifications, evidence of continuous learning. A bootcamp grad with strong projects can score well for roles that don't strictly require degrees.

**Overall Score (0-100):**
Your holistic recruiter assessment. This is NOT a simple average — weigh required skills and experience most heavily, but also consider overall candidate potential and fit.

**Recommendation:**
- "strong_match" — you would advance this candidate to interview
- "possible_match" — worth considering, has notable gaps but also strengths
- "weak_match" — significant gaps, unlikely to be a good fit

**Matched Skills:** List skills the candidate demonstrably has (from required + preferred).
**Missing Skills:** List skills the candidate lacks (from required + preferred).
**Explanation:** Write 2-4 sentences as a recruiter summary — strengths, concerns, and overall assessment.
"""


def score_match(
    resume: Resume,
    job: JobDescription,
    resume_text: str,
    job_text: str,
) -> MatchResult:
    """Score a resume against a job description using LLM-based recruiter evaluation.

    Uses Instructor to get a structured MatchResult directly from the LLM.
    Both raw text and structured data are provided so the LLM can assess
    presentation quality and factual match.
    """
    client = get_client()

    user_content = (
        "=== RAW RESUME TEXT ===\n"
        f"{resume_text}\n\n"
        "=== RAW JOB DESCRIPTION TEXT ===\n"
        f"{job_text}\n\n"
        "=== STRUCTURED RESUME DATA ===\n"
        f"{resume.model_dump_json(indent=2)}\n\n"
        "=== STRUCTURED JOB DATA ===\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        f"Evaluate this candidate ({resume.full_name}) for the {job.job_title} position. "
        "Provide your complete recruiter assessment."
    )

    logger.info("Scoring match with LLM (max_retries=3)...")

    result = client.messages.create(
        model=get_model(),
        max_tokens=4096,
        system=SCORER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        response_model=MatchResult,
        max_retries=3,
    )

    logger.info(
        "Match scored: %s → %s = %.1f (%s)",
        result.candidate_name,
        result.job_title,
        result.overall_score,
        result.recommendation,
    )
    return result
