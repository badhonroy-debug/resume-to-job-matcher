"""Generate natural-language match explanations using Claude."""

import anthropic

from resume_matcher.config import get_api_key, get_model
from resume_matcher.schemas import JobDescription, MatchResult, Resume

EXPLANATION_SYSTEM_PROMPT = """\
You are a recruiting analyst. Given a candidate's resume, a job description,
and a score breakdown, write a concise 3-5 sentence explanation of the match.

Cover:
1. Key strengths the candidate brings to this role.
2. Notable skill or experience gaps.
3. A brief interview recommendation.

Do NOT change or comment on the numerical scores — just explain the match.
Return ONLY the explanation text, no headers or formatting.
"""


def generate_explanation(
    resume: Resume, job: JobDescription, result: MatchResult
) -> str:
    """Call Claude to generate a human-readable match explanation.

    This does NOT modify the scores — it only fills in the explanation field.
    """
    # Use the raw Anthropic client (not Instructor) since we want free-form
    # text back, not a structured Pydantic model.
    client = anthropic.Anthropic(api_key=get_api_key())

    context = (
        f"Candidate: {resume.full_name}\n"
        f"Job: {job.job_title} at {job.company or 'Unknown Company'}\n"
        f"Overall Score: {result.overall_score}/100\n"
        f"Required Skills Score: {result.breakdown.required_skills_score}/100\n"
        f"Experience Score: {result.breakdown.experience_score}/100\n"
        f"Education Score: {result.breakdown.education_score}/100\n"
        f"Matched Skills: {', '.join(result.matched_skills) or 'None'}\n"
        f"Missing Skills: {', '.join(result.missing_skills) or 'None'}\n"
        f"Candidate Experience: {resume.total_years_experience} years\n"
        f"Required Experience: {job.min_years_experience} years\n"
        f"Recommendation: {result.recommendation}\n"
    )

    response = client.messages.create(
        model=get_model(),
        max_tokens=1024,
        system=EXPLANATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    return response.content[0].text.strip()
