import json

import pytest

from skillbuddy.agents.job_matcher import JobMatcherAgent


@pytest.fixture
def matcher():
    return JobMatcherAgent()


def test_parse_matches_success(matcher):
    payload = {
        "matches": [
            {
                "posting": {
                    "title": "Backend Engineer",
                    "company_name": "TechCorp",
                    "location": "Remote",
                    "description": "Design APIs",
                    "apply_link": "https://example.com",
                    "detected_skills": ["Python", "Django"],
                },
                "match_score": 0.85,
                "missing_skills": ["Go"],
            }
        ]
    }
    matches = matcher._parse_matches(json.dumps(payload))
    assert len(matches) == 1
    assert matches[0].match_score == 0.85
    assert matches[0].posting.company_name == "TechCorp"


def test_parse_matches_failure(matcher):
    with pytest.raises(RuntimeError):
        matcher._parse_matches("not-json")

