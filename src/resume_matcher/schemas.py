"""Pydantic v2 models for resume matching."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


SkillCategory = str  # e.g. "programming_language", "framework", "tool", "soft_skill", "other"

EducationLevel = str  # "none", "high_school", "bachelors", "masters", "phd"

Recommendation = str  # "strong_match", "possible_match", "weak_match"


class Skill(BaseModel):
    """A single skill extracted from a resume or job description."""

    name: str = Field(description="Normalized skill name, e.g. 'Python', 'JavaScript'")
    category: str = Field(
        description="Skill category: programming_language, framework, tool, database, cloud, soft_skill, or other"
    )


class WorkExperience(BaseModel):
    """A single work experience entry."""

    job_title: str
    company: str
    dates: str = Field(description="Date range as written, e.g. 'Jan 2020 - Present'")
    duration_months: Optional[int] = Field(
        default=None, description="Approximate duration in months"
    )
    highlights: list[str] = Field(
        default_factory=list, description="Key achievements or responsibilities"
    )


class Education(BaseModel):
    """An education entry."""

    degree: str = Field(description="Degree type, e.g. 'Bachelor of Science'")
    field: str = Field(description="Field of study, e.g. 'Computer Science'")
    institution: str
    graduation_year: Optional[int] = None

    @field_validator("graduation_year")
    @classmethod
    def validate_graduation_year(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        current_year = datetime.now().year
        if v < 1950 or v > current_year + 6:
            raise ValueError(
                f"Graduation year must be between 1950 and {current_year + 6}, got {v}"
            )
        return v


class Resume(BaseModel):
    """Structured resume data extracted by the LLM."""

    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    total_years_experience: float = Field(
        default=0, description="Total years of professional experience"
    )

    @field_validator("total_years_experience")
    @classmethod
    def validate_years(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"Total years experience cannot be negative, got {v}")
        return v


class JobDescription(BaseModel):
    """Structured job description data extracted by the LLM."""

    job_title: str
    company: Optional[str] = None
    required_skills: list[Skill] = Field(default_factory=list)
    preferred_skills: list[Skill] = Field(default_factory=list)
    min_years_experience: float = Field(default=0)
    education_level: str = Field(
        default="none",
        description="Minimum education: none, high_school, bachelors, masters, phd",
    )
    responsibilities: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """Breakdown of the match score into component parts."""

    required_skills_score: float = Field(ge=0, le=100)
    preferred_skills_score: float = Field(ge=0, le=100)
    experience_score: float = Field(ge=0, le=100)
    education_score: float = Field(ge=0, le=100)


class MatchResult(BaseModel):
    """Final match result for a candidate-job pair."""

    candidate_name: str
    job_title: str
    overall_score: float = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    explanation: str = Field(default="")
    recommendation: str = Field(
        description="One of: strong_match, possible_match, weak_match"
    )

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        allowed = {"strong_match", "possible_match", "weak_match"}
        if v not in allowed:
            raise ValueError(f"Recommendation must be one of {allowed}, got '{v}'")
        return v
