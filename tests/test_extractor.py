"""Tests for the extractor module using mocked LLM client. No real API calls."""

from unittest.mock import MagicMock, patch

import pytest

from resume_matcher.schemas import (
    Education,
    JobDescription,
    Resume,
    Skill,
    WorkExperience,
)


@pytest.fixture
def mock_resume():
    """A pre-built Resume object that the mock client will return."""
    return Resume(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="555-1234",
        summary="Experienced engineer",
        skills=[
            Skill(name="Python", category="programming_language"),
            Skill(name="Docker", category="tool"),
        ],
        experience=[
            WorkExperience(
                job_title="Software Engineer",
                company="TechCo",
                dates="2020 - Present",
                duration_months=48,
                highlights=["Built APIs", "Led team"],
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                institution="MIT",
                graduation_year=2020,
            )
        ],
        total_years_experience=4.0,
    )


@pytest.fixture
def mock_job():
    """A pre-built JobDescription object that the mock client will return."""
    return JobDescription(
        job_title="Backend Engineer",
        company="StartupXYZ",
        required_skills=[
            Skill(name="Python", category="programming_language"),
            Skill(name="PostgreSQL", category="database"),
        ],
        preferred_skills=[
            Skill(name="Docker", category="tool"),
        ],
        min_years_experience=3,
        education_level="bachelors",
        responsibilities=["Build APIs", "Design systems"],
    )


class TestExtractResume:
    @patch("resume_matcher.extractor.get_client")
    def test_extract_resume_returns_resume(self, mock_get_client, mock_resume):
        """Verify extract_resume calls the client and returns a Resume."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resume
        mock_get_client.return_value = mock_client

        from resume_matcher.extractor import extract_resume

        result = extract_resume("Some resume text here")

        assert isinstance(result, Resume)
        assert result.full_name == "Jane Doe"
        assert len(result.skills) == 2
        assert result.total_years_experience == 4.0

        # Verify the client was called with expected parameters
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_retries"] == 3
        assert call_kwargs["response_model"] is Resume

    @patch("resume_matcher.extractor.get_client")
    def test_extract_resume_passes_text_as_message(self, mock_get_client, mock_resume):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resume
        mock_get_client.return_value = mock_client

        from resume_matcher.extractor import extract_resume

        extract_resume("Full resume content goes here")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Full resume content goes here"


class TestExtractJob:
    @patch("resume_matcher.extractor.get_client")
    def test_extract_job_returns_job_description(self, mock_get_client, mock_job):
        """Verify extract_job calls the client and returns a JobDescription."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_job
        mock_get_client.return_value = mock_client

        from resume_matcher.extractor import extract_job

        result = extract_job("Some job description text")

        assert isinstance(result, JobDescription)
        assert result.job_title == "Backend Engineer"
        assert len(result.required_skills) == 2
        assert result.min_years_experience == 3

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_retries"] == 3
        assert call_kwargs["response_model"] is JobDescription

    @patch("resume_matcher.extractor.get_client")
    def test_extract_job_passes_text_as_message(self, mock_get_client, mock_job):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_job
        mock_get_client.return_value = mock_client

        from resume_matcher.extractor import extract_job

        extract_job("Job posting text here")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Job posting text here"


class TestConfigError:
    @patch("resume_matcher.extractor.get_client")
    def test_config_error_propagates(self, mock_get_client):
        """If get_client raises ConfigError, it should propagate."""
        from resume_matcher.config import ConfigError

        mock_get_client.side_effect = ConfigError("No API key")

        from resume_matcher.extractor import extract_resume

        with pytest.raises(ConfigError, match="No API key"):
            extract_resume("some text")
