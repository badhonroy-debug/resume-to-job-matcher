"""Tests for the FastAPI web application."""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from resume_matcher.config import ConfigError
from resume_matcher.schemas import (
    Education,
    JobDescription,
    MatchResult,
    Resume,
    ScoreBreakdown,
    Skill,
    WorkExperience,
)
from resume_matcher.web import app

client = TestClient(app)

# ── Fixtures ──

SAMPLE_RESUME = Resume(
    full_name="Jane Doe",
    email="jane@example.com",
    summary="Senior engineer",
    skills=[Skill(name="Python", category="programming_language")],
    experience=[
        WorkExperience(
            job_title="Engineer",
            company="Acme",
            dates="2020-Present",
            duration_months=48,
            highlights=["Built APIs"],
        )
    ],
    education=[
        Education(
            degree="BS",
            field="Computer Science",
            institution="MIT",
            graduation_year=2019,
        )
    ],
    total_years_experience=5.0,
)

SAMPLE_JOB = JobDescription(
    job_title="Backend Engineer",
    company="TechCo",
    required_skills=[Skill(name="Python", category="programming_language")],
    preferred_skills=[Skill(name="Go", category="programming_language")],
    min_years_experience=3,
    education_level="bachelors",
    responsibilities=["Build APIs"],
)

SAMPLE_MATCH = MatchResult(
    candidate_name="Jane Doe",
    job_title="Backend Engineer",
    overall_score=82.0,
    breakdown=ScoreBreakdown(
        required_skills_score=90.0,
        preferred_skills_score=40.0,
        experience_score=85.0,
        education_score=80.0,
    ),
    matched_skills=["Python"],
    missing_skills=["Go"],
    explanation="Strong candidate.",
    recommendation="strong_match",
)


# ── Health endpoint ──


class TestHealth:
    def test_health_ok(self):
        with patch("resume_matcher.web.get_api_key", return_value="sk-ant-real"):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["api_key_configured"] is True

    def test_health_no_key(self):
        with patch("resume_matcher.web.get_api_key", side_effect=ConfigError("no key")):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["api_key_configured"] is False


# ── Home page ──


class TestHomePage:
    def test_home_returns_html(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Resume Matcher" in resp.text
        assert "text/html" in resp.headers["content-type"]


# ── Extract Resume ──


class TestExtractResume:
    @patch("resume_matcher.web.extract_resume", return_value=SAMPLE_RESUME)
    def test_extract_resume_text(self, mock_extract):
        resp = client.post("/api/extract-resume", data={"text": "Jane Doe resume..."})
        assert resp.status_code == 200
        body = resp.json()
        assert body["full_name"] == "Jane Doe"
        mock_extract.assert_called_once()

    @patch("resume_matcher.web.extract_resume", return_value=SAMPLE_RESUME)
    def test_extract_resume_file(self, mock_extract):
        resp = client.post(
            "/api/extract-resume",
            files={"file": ("resume.txt", io.BytesIO(b"Jane Doe resume content"), "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Jane Doe"

    def test_extract_resume_no_input(self):
        resp = client.post("/api/extract-resume", data={"text": ""})
        assert resp.status_code == 400

    @patch("resume_matcher.web.extract_resume", side_effect=ConfigError("no key"))
    def test_extract_resume_config_error(self, mock_extract):
        resp = client.post("/api/extract-resume", data={"text": "some resume"})
        assert resp.status_code == 500


# ── Extract Job ──


class TestExtractJob:
    @patch("resume_matcher.web.extract_job", return_value=SAMPLE_JOB)
    def test_extract_job_text(self, mock_extract):
        resp = client.post("/api/extract-job", data={"text": "Backend Engineer posting..."})
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_title"] == "Backend Engineer"
        mock_extract.assert_called_once()

    @patch("resume_matcher.web.extract_job", return_value=SAMPLE_JOB)
    def test_extract_job_file(self, mock_extract):
        resp = client.post(
            "/api/extract-job",
            files={"file": ("job.txt", io.BytesIO(b"Job posting content"), "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["job_title"] == "Backend Engineer"

    def test_extract_job_no_input(self):
        resp = client.post("/api/extract-job", data={"text": "  "})
        assert resp.status_code == 400


# ── Match ──


class TestMatch:
    @patch("resume_matcher.web.generate_explanation", return_value="Great fit.")
    @patch("resume_matcher.web.score_match", return_value=SAMPLE_MATCH)
    @patch("resume_matcher.web.extract_job", return_value=SAMPLE_JOB)
    @patch("resume_matcher.web.extract_resume", return_value=SAMPLE_RESUME)
    def test_match_text(self, mock_er, mock_ej, mock_score, mock_explain):
        resp = client.post(
            "/api/match",
            data={"resume_text": "Jane resume", "job_text": "Backend job"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_score"] == 82.0
        assert body["recommendation"] == "strong_match"
        mock_er.assert_called_once()
        mock_ej.assert_called_once()
        mock_score.assert_called_once()
        mock_explain.assert_called_once()

    def test_match_missing_resume(self):
        resp = client.post("/api/match", data={"job_text": "some job"})
        assert resp.status_code == 400

    def test_match_missing_job(self):
        resp = client.post("/api/match", data={"resume_text": "some resume"})
        assert resp.status_code == 400


# ── Rank ──


class TestRank:
    @patch("resume_matcher.web.score_match", return_value=SAMPLE_MATCH)
    @patch("resume_matcher.web.extract_resume", return_value=SAMPLE_RESUME)
    @patch("resume_matcher.web.extract_job", return_value=SAMPLE_JOB)
    def test_rank_with_files(self, mock_ej, mock_er, mock_score):
        resp = client.post(
            "/api/rank",
            files=[
                ("resume_files", ("r1.txt", io.BytesIO(b"Resume 1"), "text/plain")),
                ("resume_files", ("r2.txt", io.BytesIO(b"Resume 2"), "text/plain")),
            ],
            data={"job_text": "Backend job"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2

    @patch("resume_matcher.web.score_match", return_value=SAMPLE_MATCH)
    @patch("resume_matcher.web.extract_resume", return_value=SAMPLE_RESUME)
    @patch("resume_matcher.web.extract_job", return_value=SAMPLE_JOB)
    def test_rank_with_pasted_text(self, mock_ej, mock_er, mock_score):
        resp = client.post(
            "/api/rank",
            data={
                "resume_texts": "Resume One\n---\nResume Two",
                "job_text": "Backend job",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2

    def test_rank_no_resumes(self):
        resp = client.post("/api/rank", data={"job_text": "some job"})
        assert resp.status_code == 400

    def test_rank_no_job(self):
        resp = client.post(
            "/api/rank",
            data={"resume_texts": "some resume"},
        )
        assert resp.status_code == 400
