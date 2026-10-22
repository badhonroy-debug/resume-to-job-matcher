"""Tests for Pydantic schema validation."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from resume_matcher.schemas import (
    Education,
    MatchResult,
    Resume,
    ScoreBreakdown,
    Skill,
    WorkExperience,
)


class TestSkill:
    def test_valid_skill(self):
        s = Skill(name="Python", category="programming_language")
        assert s.name == "Python"
        assert s.category == "programming_language"


class TestEducation:
    def test_valid_graduation_year(self):
        e = Education(degree="BS", field="CS", institution="MIT", graduation_year=2020)
        assert e.graduation_year == 2020

    def test_none_graduation_year(self):
        e = Education(degree="BS", field="CS", institution="MIT")
        assert e.graduation_year is None

    def test_graduation_year_too_old(self):
        with pytest.raises(ValidationError, match="1950"):
            Education(degree="BS", field="CS", institution="MIT", graduation_year=1900)

    def test_graduation_year_too_far_future(self):
        future_year = datetime.now().year + 7
        with pytest.raises(ValidationError, match="Graduation year"):
            Education(
                degree="BS", field="CS", institution="MIT", graduation_year=future_year
            )

    def test_graduation_year_near_future_ok(self):
        near_future = datetime.now().year + 5
        e = Education(
            degree="BS", field="CS", institution="MIT", graduation_year=near_future
        )
        assert e.graduation_year == near_future


class TestResume:
    def test_valid_resume(self):
        r = Resume(
            full_name="John Doe",
            email="john@example.com",
            total_years_experience=5.0,
        )
        assert r.full_name == "John Doe"
        assert r.total_years_experience == 5.0

    def test_negative_years_rejected(self):
        with pytest.raises(ValidationError, match="negative"):
            Resume(full_name="John Doe", total_years_experience=-1)

    def test_zero_years_ok(self):
        r = Resume(full_name="John Doe", total_years_experience=0)
        assert r.total_years_experience == 0

    def test_defaults(self):
        r = Resume(full_name="Jane Doe")
        assert r.skills == []
        assert r.experience == []
        assert r.education == []
        assert r.total_years_experience == 0
        assert r.email is None


class TestScoreBreakdown:
    def test_valid_scores(self):
        sb = ScoreBreakdown(
            required_skills_score=80,
            preferred_skills_score=60,
            experience_score=100,
            education_score=50,
        )
        assert sb.required_skills_score == 80

    def test_score_over_100_rejected(self):
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                required_skills_score=101,
                preferred_skills_score=60,
                experience_score=100,
                education_score=50,
            )

    def test_negative_score_rejected(self):
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                required_skills_score=-1,
                preferred_skills_score=60,
                experience_score=100,
                education_score=50,
            )

    def test_boundary_values(self):
        sb = ScoreBreakdown(
            required_skills_score=0,
            preferred_skills_score=0,
            experience_score=100,
            education_score=100,
        )
        assert sb.required_skills_score == 0
        assert sb.experience_score == 100


class TestMatchResult:
    def _make_result(self, **kwargs):
        defaults = {
            "candidate_name": "Test User",
            "job_title": "Test Job",
            "overall_score": 75,
            "breakdown": ScoreBreakdown(
                required_skills_score=80,
                preferred_skills_score=60,
                experience_score=70,
                education_score=90,
            ),
            "matched_skills": ["Python"],
            "missing_skills": ["Go"],
            "explanation": "Good match",
            "recommendation": "strong_match",
        }
        defaults.update(kwargs)
        return MatchResult(**defaults)

    def test_valid_match_result(self):
        r = self._make_result()
        assert r.candidate_name == "Test User"
        assert r.recommendation == "strong_match"

    def test_overall_score_over_100_rejected(self):
        with pytest.raises(ValidationError):
            self._make_result(overall_score=101)

    def test_overall_score_negative_rejected(self):
        with pytest.raises(ValidationError):
            self._make_result(overall_score=-5)

    def test_invalid_recommendation_rejected(self):
        with pytest.raises(ValidationError, match="Recommendation"):
            self._make_result(recommendation="excellent")

    def test_all_recommendations_accepted(self):
        for rec in ("strong_match", "possible_match", "weak_match"):
            r = self._make_result(recommendation=rec)
            assert r.recommendation == rec
