"""Interview coaching utilities for question generation and response evaluation."""
from __future__ import annotations

import json
from typing import List, Optional, Tuple

from google.genai import Client
from google.genai import types as genai_types

from skillbuddy.config import google_api_key
from skillbuddy.types.interview import (
    InterviewFeedback,
    InterviewQuestions,
    InterviewQuestion,
    InterviewEvaluation,
    MCQQuiz,
    LiveInterviewQuestion,
    LiveInterviewQuestions,
    LiveAnswerFeedback,
    LiveInterviewResult,
)
from skillbuddy.types.profile import ResumeProfile

MODEL_ID = "gemini-flash-latest"
LIVE_MODEL_ID = "gemini-2.5-flash-native-audio-preview-09-2025"  # For audio/video streaming


class InterviewCoach:
    """Generates targeted interview questions and evaluates responses."""

    def __init__(self) -> None:
        self._client = Client(api_key=google_api_key())

    # =====================
    # LIVE INTERVIEW METHODS
    # =====================
    
    def generate_live_interview_questions(self, profile: ResumeProfile, target_role: str) -> List[LiveInterviewQuestion]:
        """Generate 7 questions for live interview mode."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are a professional interviewer conducting a live interview. Generate exactly 7 questions in this order:

1. Q1 (intro): "Tell me about yourself" - standard opening
2. Q2 (project): Question about their first/main project mentioned in resume
3. Q3 (project): Question about another project or deeper dive into first project
4. Q4 (technical): Deep-dive technical question about a specific tool/technology they used (e.g., LangChain, OCR, CNN, RAG, Python specifics)
5. Q5 (technical): Another technical question on a different skill/tool
6. Q6 (problem_solving): Scenario-based problem-solving question related to their domain
7. Q7 (hr_culture): HR/culture fit question (teamwork, conflict resolution, career goals)

Questions must:
- Be specific to the candidate's actual resume content
- Be professional and concise
- Only ask ONE thing at a time
- Be appropriate for their experience level

Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=LiveInterviewQuestions,
        )
        
        skills = ", ".join(profile.skills) if profile.skills else "General programming"
        projects_info = "\n".join([
            f"- {p.name}: {p.description or 'No description'} (Tech: {', '.join(p.technologies) if p.technologies else 'Not specified'})"
            for p in profile.projects
        ]) if profile.projects else "No projects listed"
        
        prompt = f"""Generate 7 live interview questions for this candidate.

Target Role: {target_role}
Candidate Level: {profile.level or 'Not specified'}
Skills: {skills}

Projects:
{projects_info}

Summary: {profile.summary or 'Not provided'}

Generate professional, specific questions following the required structure."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to generate live interview questions")
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        questions = LiveInterviewQuestions(**data)
        return questions.questions

    def check_answer_clarity(self, question: str, answer: str, profile: ResumeProfile) -> LiveAnswerFeedback:
        """Check if an answer needs clarification before moving to next question."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are an interviewer checking if a candidate's answer is clear and complete.

Evaluate:
- Is the answer understandable and on-topic?
- Did they provide enough detail?
- Is clarification needed?

If the answer is vague, too short, or off-topic, request clarification politely.
If the answer is acceptable (even if not perfect), mark as clear and provide brief feedback.

Be professional and encouraging. Don't be overly critical.
Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=LiveAnswerFeedback,
        )
        
        prompt = f"""Question: {question}

Candidate's Answer: {answer}

Candidate Skills: {', '.join(profile.skills)}

Is this answer clear enough to proceed, or should we ask for clarification?"""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            # Default to accepting the answer
            return LiveAnswerFeedback(
                is_clear=True,
                needs_clarification=False,
                brief_feedback="Answer noted."
            )
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        return LiveAnswerFeedback(**data)

    def evaluate_live_interview(
        self,
        questions: List[LiveInterviewQuestion],
        answers: List[str],
        profile: ResumeProfile,
    ) -> LiveInterviewResult:
        """Evaluate the complete live interview and provide final scores."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are an expert interview evaluator. Provide a comprehensive evaluation of the live interview.

Evaluate:
1. Interview Score (1-10): Overall performance considering technical knowledge, communication, and relevance
2. Strengths in Answering: What the candidate did well
3. Improvement Areas: Specific areas to work on
4. Communication Score (1-10): Clarity, structure, and professionalism
5. Weak Points: Specific topics or skills that need more preparation
6. Suggestions: Actionable advice for improvement

Be fair, specific, and constructive. Focus on helping the candidate improve.
Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=LiveInterviewResult,
        )
        
        qa_pairs = "\n\n".join([
            f"Q{q.question_number} ({q.category}): {q.question}\nAnswer: {a}"
            for q, a in zip(questions, answers)
        ])
        
        prompt = f"""Evaluate this complete live interview.

Candidate Profile:
- Level: {profile.level or 'Not specified'}
- Skills: {', '.join(profile.skills)}

Interview Transcript:
{qa_pairs}

Provide comprehensive evaluation."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to evaluate live interview")
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        return LiveInterviewResult(**data)

    # =====================
    # STANDARD INTERVIEW METHODS
    # =====================

    def generate_questions(self, profile: ResumeProfile, target_role: str, num_questions: int = 5) -> List[InterviewQuestion]:
        """Generate interview questions based on candidate's projects, tools, and skills."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are an expert technical interviewer. Generate interview questions based on the candidate's resume.

Question types to include:
1. Project Architecture Explanation - Ask about system design, architecture decisions
2. Challenges Faced & Solutions - Real problems encountered and how they solved them  
3. Technology Deep Dive - In-depth questions about specific tools/frameworks they used
4. Real-World Application - How they would apply their skills to practical scenarios
5. Optimization & Scalability - Performance, scaling, and efficiency questions

Questions must be:
- Specific to the candidate's actual projects and skills mentioned
- Challenging but fair for their experience level
- Open-ended to allow detailed responses
- Technical but also assess problem-solving approach

Return exactly 5 questions, one from each category.""",
            response_mime_type="application/json",
            response_schema=InterviewQuestions,
        )
        
        skills = ", ".join(profile.skills) if profile.skills else "General programming"
        projects_info = "\n".join([
            f"- {p.name}: {p.description or 'No description'} (Tech: {', '.join(p.technologies) if p.technologies else 'Not specified'})"
            for p in profile.projects
        ]) if profile.projects else "No projects listed"
        
        experience_info = "\n".join([
            f"- {e.title} at {e.company or 'Unknown'}: {', '.join(e.highlights[:2]) if e.highlights else 'No highlights'}"
            for e in profile.experience
        ]) if profile.experience else "No experience listed"

        prompt = f"""Generate 5 technical interview questions for this candidate.

Target Role: {target_role}
Candidate Level: {profile.level or 'Not specified'}

Skills: {skills}

Projects:
{projects_info}

Experience:
{experience_info}

Generate specific, challenging questions that test their actual knowledge."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to generate interview questions")
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        questions = InterviewQuestions(**data)
        return questions.questions[:num_questions]

    def evaluate_answers(
        self,
        questions: List[InterviewQuestion],
        answers: List[str],
        profile: ResumeProfile,
    ) -> InterviewEvaluation:
        """Evaluate all candidate answers and provide comprehensive feedback."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are an expert interview evaluator. Assess the candidate's answers comprehensively.

For each answer, evaluate:
- Technical accuracy and depth
- Relevance to the question asked
- Use of specific examples from their experience
- Problem-solving approach demonstrated

Also assess soft skills:
- Communication clarity (how well they explain concepts)
- Answer structure (logical flow, STAR method usage)
- Confidence (based on language used, specificity)

Be fair but thorough. Identify specific weak topics they should study more.
Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=InterviewEvaluation,
        )
        
        qa_pairs = "\n\n".join([
            f"Question {i+1} ({q.category}):\n{q.question}\n\nAnswer {i+1}:\n{a}"
            for i, (q, a) in enumerate(zip(questions, answers))
        ])
        
        prompt = f"""Evaluate these interview responses.

Candidate Skills: {', '.join(profile.skills)}
Candidate Level: {profile.level or 'Not specified'}

{qa_pairs}

Provide detailed evaluation with scores, strengths, improvements, and soft skills assessment."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to evaluate interview answers")
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        return InterviewEvaluation(**data)

    def generate_mcq_quiz(self, profile: ResumeProfile) -> MCQQuiz:
        """Generate MCQ quiz based on candidate's resume topics."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are a technical quiz creator. Generate MCQ questions based on the candidate's skills and projects.

Create 5 multiple-choice questions that:
- Test practical knowledge of technologies they claim to know
- Cover different topics from their resume (projects, tools, concepts)
- Have one clearly correct answer and three plausible distractors
- Are at an appropriate difficulty for their experience level
- Include brief explanations for the correct answers

Topics to cover based on resume: AI/ML concepts, programming, frameworks, tools, algorithms, system design.
Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=MCQQuiz,
        )
        
        skills = ", ".join(profile.skills) if profile.skills else "General programming"
        projects = ", ".join([p.name for p in profile.projects]) if profile.projects else "No projects"
        technologies = set()
        for p in profile.projects:
            technologies.update(p.technologies)
        tech_str = ", ".join(technologies) if technologies else skills

        prompt = f"""Create a 5-question MCQ quiz for this candidate.

Candidate Level: {profile.level or 'Not specified'}
Skills: {skills}
Projects: {projects}
Technologies Used: {tech_str}

Generate questions that test their claimed expertise. Questions should be practical and relevant."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to generate MCQ quiz")
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        return MCQQuiz(**data)

    def generate_question(self, profile: ResumeProfile, target_role: str) -> str:
        """Generate a single interview question (legacy method)."""
        questions = self.generate_questions(profile, target_role, num_questions=1)
        if questions:
            return questions[0].question
        return "Tell me about your most challenging project."

    def evaluate_response(
        self,
        question: str,
        audio_bytes: bytes,
        profile: ResumeProfile,
        video_bytes: Optional[bytes] = None,
        transcript: Optional[str] = None,
    ) -> InterviewFeedback:
        """Evaluate a single audio/video response (legacy method for multimodal)."""
        parts = []
        if audio_bytes:
            parts.append(genai_types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"))
        if video_bytes:
            parts.append(genai_types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"))
        summary = self._evaluation_prompt(profile, question, transcript)
        parts.append(genai_types.Part.from_text(text=summary))

        config = genai_types.GenerateContentConfig(
            system_instruction=(
                "You evaluate interview answers. Provide constructive feedback, recognize strengths,"
                " count filler words when possible, and highlight delivery improvements."
                " Respond strictly as JSON matching the InterviewFeedback schema."
            ),
            response_mime_type="application/json",
            response_schema=InterviewFeedback,
        )

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=parts)],
            config=config,
        )
        return self._parse_feedback(response.candidates[0].content.parts[0].text)

    def _evaluation_prompt(self, profile: ResumeProfile, question: str, transcript: Optional[str]) -> str:
        base = (
            f"Question: {question}\n"
            f"Candidate core skills: {', '.join(profile.skills)}\n"
            "Assess the recorded answer for technical correctness, communication clarity, and confidence."
        )
        if transcript:
            base += f"\nTranscript (approximate): {transcript}"
        return base

    def _parse_feedback(self, payload: str) -> InterviewFeedback:
        text = self._strip_markdown_fences(payload)
        try:
            data = json.loads(text)
            return InterviewFeedback(**data)
        except Exception as exc:
            raise RuntimeError("Failed to parse interview feedback JSON") from exc

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove markdown code fences if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines).strip()
        return text

    # =====================
    # AUDIO INTERVIEW METHODS
    # =====================

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """Transcribe audio to text using Gemini."""
        config = genai_types.GenerateContentConfig(
            system_instruction="You are a transcription assistant. Transcribe the audio exactly as spoken. Return only the transcription, no additional text."
        )
        
        parts = [
            genai_types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            genai_types.Part.from_text(text="Transcribe this audio exactly as spoken.")
        ]
        
        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=parts)],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to transcribe audio")
        
        return response.candidates[0].content.parts[0].text.strip()

    def process_audio_answer(
        self,
        question: str,
        audio_bytes: bytes,
        profile: ResumeProfile,
        mime_type: str = "audio/wav"
    ) -> tuple[str, LiveAnswerFeedback]:
        """Process an audio answer: transcribe and check clarity."""
        # Transcribe the audio
        transcript = self.transcribe_audio(audio_bytes, mime_type)
        
        # Check answer clarity
        feedback = self.check_answer_clarity(question, transcript, profile)
        
        return transcript, feedback

    def generate_spoken_question(self, question: str) -> str:
        """Generate a natural speaking version of the question for TTS."""
        # For now, just return the question as-is
        # Could be enhanced with more natural phrasing
        return question
