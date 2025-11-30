"""Pydantic models for multimodal coaching outputs."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DeliveryFeedback(BaseModel):
    filler_count: Optional[int] = Field(default=None, description="Estimated filler words count")
    tone: Optional[str] = Field(default=None, description="Tone or confidence analysis")
    visual_observation: Optional[str] = Field(
        default=None, description="High level comment about visual communication"
    )


class InterviewFeedback(BaseModel):
    question: str = Field(description="Prompt asked to the candidate")
    answer_quality: str = Field(description="Content-oriented evaluation")
    delivery: DeliveryFeedback = Field(default_factory=DeliveryFeedback, description="Communication feedback")
    improvement_tips: str = Field(description="Actionable suggestions for the candidate")


class InterviewQuestion(BaseModel):
    """A single interview question."""
    question: str = Field(description="The interview question")
    category: str = Field(description="Question type: project_architecture, challenges, technology_deep_dive, real_world_application, optimization_scalability")
    context: Optional[str] = Field(default=None, description="Context about why this question is relevant")


class InterviewQuestions(BaseModel):
    """Set of interview questions based on resume."""
    questions: List[InterviewQuestion] = Field(description="List of 5 interview questions")


class AnswerEvaluation(BaseModel):
    """Evaluation of a single answer."""
    question_number: int = Field(description="Question number (1-5)")
    score: int = Field(ge=1, le=10, description="Score out of 10")
    strengths: List[str] = Field(default_factory=list, description="What was good about the answer")
    improvements: List[str] = Field(default_factory=list, description="Areas to improve")
    missing_points: List[str] = Field(default_factory=list, description="Key points that were missed")


class SoftSkillAssessment(BaseModel):
    """Soft skills evaluation."""
    communication_clarity: int = Field(ge=1, le=10, description="Clarity of communication (1-10)")
    structure: int = Field(ge=1, le=10, description="Answer structure and organization (1-10)")
    confidence: int = Field(ge=1, le=10, description="Confidence level (1-10)")
    feedback: str = Field(description="Overall soft skills feedback")


class InterviewEvaluation(BaseModel):
    """Complete evaluation of all interview answers."""
    overall_score: int = Field(ge=1, le=10, description="Overall interview score (1-10)")
    evaluations: List[AnswerEvaluation] = Field(description="Individual answer evaluations")
    overall_strengths: List[str] = Field(default_factory=list, description="Overall strong points")
    overall_improvements: List[str] = Field(default_factory=list, description="Overall areas to improve")
    weak_topics: List[str] = Field(default_factory=list, description="Topics needing more preparation")
    soft_skills: SoftSkillAssessment = Field(description="Soft skills assessment")


class MCQOption(BaseModel):
    """A single MCQ option."""
    label: str = Field(description="Option label (A, B, C, D)")
    text: str = Field(description="Option text")


class MCQQuestion(BaseModel):
    """A single MCQ question."""
    question_number: int = Field(description="Question number (1-5)")
    question: str = Field(description="The quiz question")
    options: List[MCQOption] = Field(description="Four options A, B, C, D")
    correct_answer: str = Field(description="Correct option label (A, B, C, or D)")
    explanation: str = Field(description="Brief explanation of why the answer is correct")


class MCQQuiz(BaseModel):
    """Set of MCQ questions based on resume topics."""
    questions: List[MCQQuestion] = Field(description="List of 5 MCQ questions")


# Live Interview Types
class LiveInterviewQuestion(BaseModel):
    """A question in the live interview flow."""
    question_number: int = Field(description="Question number (1-7)")
    question: str = Field(description="The interview question")
    category: str = Field(description="intro, project, technical, problem_solving, hr_culture")


class LiveInterviewQuestions(BaseModel):
    """Complete set of live interview questions."""
    questions: List[LiveInterviewQuestion] = Field(description="List of 7 interview questions")


class LiveAnswerFeedback(BaseModel):
    """Feedback for a single live interview answer."""
    is_clear: bool = Field(description="Whether the answer was clear and understandable")
    needs_clarification: bool = Field(description="Whether clarification is needed")
    clarification_prompt: Optional[str] = Field(default=None, description="Follow-up question if clarification needed")
    brief_feedback: str = Field(description="One-line feedback on the answer")


class LiveInterviewResult(BaseModel):
    """Final evaluation after live interview."""
    interview_score: int = Field(ge=1, le=10, description="Overall interview score (1-10)")
    strengths_in_answering: List[str] = Field(description="Strengths observed in answers")
    improvement_areas: List[str] = Field(description="Areas that need improvement")
    communication_score: int = Field(ge=1, le=10, description="Communication clarity score (1-10)")
    weak_points: List[str] = Field(description="Weak points identified")
    suggestions: List[str] = Field(description="Suggestions to improve")

