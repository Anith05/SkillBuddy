import json
from types import SimpleNamespace

from skillbuddy.agents.interview_coach import InterviewCoach
from skillbuddy.types.interview import InterviewFeedback, InterviewQuestions
from skillbuddy.types.profile import ResumeProfile


class StubModels:
    def __init__(self, responses):
        self._responses = list(responses)

    def generate_content(self, *args, **kwargs):
        text = self._responses.pop(0)
        part = SimpleNamespace(text=text)
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        return SimpleNamespace(candidates=[candidate])


class StubClient:
    def __init__(self, responses):
        self.models = StubModels(responses)


def _profile() -> ResumeProfile:
    return ResumeProfile(skills=["Python", "React"], level="Mid")


def test_generate_question():
    # Mock response for generate_questions (returns JSON)
    questions_response = {
        "questions": [
            {
                "question": "Explain project X",
                "category": "project_architecture",
                "context": "Based on your resume"
            }
        ]
    }
    
    coach = InterviewCoach()
    coach._client = StubClient([json.dumps(questions_response)])
    question = coach.generate_question(_profile(), "React Developer")
    assert question == "Explain project X"


def test_evaluate_response():
    feedback = {
        "question": "Describe a challenge",
        "answer_quality": "Strong technical depth",
        "delivery": {
            "filler_count": 2,
            "tone": "Confident",
            "visual_observation": "Maintained eye contact",
        },
        "improvement_tips": "Tighten the ending summary",
    }

    coach = InterviewCoach()
    coach._client = StubClient([json.dumps(feedback)])

    result = coach.evaluate_response(
        question=feedback["question"],
        audio_bytes=b"fake",
        profile=_profile(),
        transcript="Sample transcript",
    )

    assert isinstance(result, InterviewFeedback)
    assert result.answer_quality == "Strong technical depth"
    assert result.delivery.filler_count == 2
    assert result.improvement_tips.startswith("Tighten")
