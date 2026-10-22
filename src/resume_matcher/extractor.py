"""Extract structured data from resume and job description text using Claude."""

import logging

from resume_matcher.config import get_model
from resume_matcher.llm_client import get_client
from resume_matcher.schemas import JobDescription, Resume

logger = logging.getLogger(__name__)

RESUME_SYSTEM_PROMPT = """\
You are a resume parser. Extract structured data from the provided resume text.

Rules:
- Extract ONLY information that is explicitly present in the text.
- Normalize skill names to their common forms (e.g. "JS" -> "JavaScript", "k8s" -> "Kubernetes").
- Calculate total_years_experience by summing durations of work experience entries.
- If dates are ambiguous, make reasonable estimates for duration_months.
- Categorize each skill as: programming_language, framework, tool, database, cloud, soft_skill, or other.
"""

JOB_SYSTEM_PROMPT = """\
You are a job description parser. Extract structured data from the provided job posting.

Rules:
- Separate required skills from preferred/nice-to-have skills.
- Normalize skill names to their common forms (e.g. "JS" -> "JavaScript", "k8s" -> "Kubernetes").
- Extract the minimum years of experience if stated.
- Determine the minimum education level required: none, high_school, bachelors, masters, or phd.
- Categorize each skill as: programming_language, framework, tool, database, cloud, soft_skill, or other.
"""


def extract_resume(text: str) -> Resume:
    """Parse resume text into a structured Resume object.

    Uses Instructor's max_retries to automatically retry if the LLM output
    doesn't match the Pydantic schema. On each retry, the validation error
    is sent back to the model so it can fix its response.
    """
    client = get_client()
    logger.info("Extracting resume data (max_retries=3)...")

    # Instructor's create call validates the response against the Resume model.
    # If validation fails (e.g. negative years, bad graduation year), Instructor
    # feeds the error back to Claude and retries up to max_retries times.
    resume = client.messages.create(
        model=get_model(),
        max_tokens=4096,
        system=RESUME_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        response_model=Resume,
        max_retries=3,
    )

    logger.info("Resume extracted for: %s", resume.full_name)
    return resume


def extract_job(text: str) -> JobDescription:
    """Parse job description text into a structured JobDescription object.

    Uses Instructor's max_retries to automatically retry if the LLM output
    doesn't match the Pydantic schema.
    """
    client = get_client()
    logger.info("Extracting job description data (max_retries=3)...")

    job = client.messages.create(
        model=get_model(),
        max_tokens=4096,
        system=JOB_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        response_model=JobDescription,
        max_retries=3,
    )

    logger.info("Job extracted: %s", job.job_title)
    return job
