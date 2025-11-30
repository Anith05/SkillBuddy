import json

import pytest

from skillbuddy.agents.resume_analyzer import ResumeAnalyzerAgent
from skillbuddy.types.profile import ResumeProfile


@pytest.fixture
def analyzer():
    return ResumeAnalyzerAgent()


def test_parse_profile_success(analyzer):
    payload = {
        "skills": ["Python", "React"],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "TechCorp",
                "duration": "2023-2024",
                "highlights": ["Built APIs"],
            }
        ],
        "projects": [
            {
                "name": "Analytics Dashboard",
                "description": "Created real-time dashboards",
                "technologies": ["Dash", "Plotly"],
            }
        ],
        "level": "Mid",
        "summary": "Full-stack developer with data viz focus",
    }
    profile = analyzer._parse_profile(json.dumps(payload))
    assert isinstance(profile, ResumeProfile)
    assert profile.skills == ["Python", "React"]
    assert profile.level == "Mid"


def test_parse_profile_failure(analyzer):
    with pytest.raises(RuntimeError):
        analyzer._parse_profile("not-json")
