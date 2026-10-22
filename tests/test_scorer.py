"""Tests for the LLM-based scorer using mocked Instructor client."""

from unittest.mock import MagicMock, patch

import pytest

from resume_matcher.config import ConfigError
from resume_matcher.schemas import (
    Education,
    JobDescription,
    MatchResult,
    Resume,
    ScoreBreakdown,
    Skill,
)
from resume_matcher.scorer import score_match


def _make_resume():
    return Resume(
        full_name="Alice Smith",
        skills=[
            Skill(name="Python", category="programming_language"),
            Skill(name="Docker", category="tool"),
        ],
        total_years_experience=5,
        education=[
            Education(degree="Bachelor of Science", field="Computer Science", institution="MIT")
        ],
    )


def _make_job():
    return JobDescription(
        job_title="Senior Backend Engineer",
        required_skills=[
            Skill(name="Python", category="programming_language"),
            Skill(name="AWS", category="cloud"),
        ],
        preferred_skills=[
            Skill(name="Docker", category="tool"),
        ],
        min_years_experience=3,
        education_level="bachelors",
    )


def _make_match_result():
    return MatchResult(
        candidate_name="Alice Smith",
        job_title="Senior Backend Engineer",
        overall_score=78.5,
        breakdown=ScoreBreakdown(
            required_skills_score=70.0,
            preferred_skills_score=90.0,
            experience_score=85.0,
            education_score=80.0,
        ),
        matched_skills=["Python", "Docker"],
        missing_skills=["AWS"],
        explanation="Strong Python background with good Docker skills. Missing AWS experience but transferable cloud knowledge likely.",
        recommendation="strong_match",
    )


@patch("resume_matcher.scorer.get_client")
@patch("resume_matcher.scorer.get_model", return_value="claude-haiku-5-5")
class TestScoreMatch:
    def test_calls_client_with_correct_params(self, mock_get_model, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.messages.create.return_value = _make_match_result()

        resume = _make_resume()
        job = _make_job()

        score_match(resume, job, "raw resume text", "raw job text")

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-5-5"
        assert call_kwargs["response_model"] is MatchResult
        assert call_kwargs["max_retries"] == 3
        assert call_kwargs["max_tokens"] == 4096

    def test_passes_raw_text_in_messages(self, mock_get_model, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.messages.create.return_value = _make_match_result()

        resume = _make_resume()
        job = _make_job()

        score_match(resume, job, "raw resume text", "raw job text")

        call_kwargs = mock_client.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]
        assert "raw resume text" in user_content
        assert "raw job text" in user_content

    def test_returns_match_result_from_llm(self, mock_get_model, mock_get_client):
        expected = _make_match_result()
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.messages.create.return_value = expected

        resume = _make_resume()
        job = _make_job()

        result = score_match(resume, job, "raw resume text", "raw job text")

        assert result is expected
        assert result.overall_score == 78.5
        assert result.recommendation == "strong_match"
        assert result.explanation != ""
        assert "Python" in result.matched_skills
        assert "AWS" in result.missing_skills

    def test_config_error_propagates(self, mock_get_model, mock_get_client):
        mock_get_client.side_effect = ConfigError("API key not set")

        resume = _make_resume()
        job = _make_job()

        with pytest.raises(ConfigError, match="API key not set"):
            score_match(resume, job, "raw resume text", "raw job text")

    def test_includes_system_prompt(self, mock_get_model, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.messages.create.return_value = _make_match_result()

        resume = _make_resume()
        job = _make_job()

        score_match(resume, job, "raw resume text", "raw job text")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "recruiter" in call_kwargs["system"].lower()
