"""Resume analyzer agent built on Google ADK."""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from google.genai import Client
from google.genai import types as genai_types

from skillbuddy.config import google_api_key
from skillbuddy.types.profile import ResumeProfile, ResumeAnalysis

MODEL_ID = "gemini-flash-latest"  # Text centric, low latency


class ResumeAnalyzerAgent:
    """Analyzes resumes and provides comprehensive feedback."""

    def __init__(self) -> None:
        self._client = Client(api_key=google_api_key())

    def analyze(self, resume_text: str, target_role: Optional[str] = None) -> ResumeProfile:
        """Synchronous helper for Streamlit usage."""
        return asyncio.run(self.analyze_async(resume_text, target_role=target_role))

    async def analyze_async(self, resume_text: str, target_role: Optional[str] = None) -> ResumeProfile:
        """Analyze resume and return comprehensive profile with analysis."""
        # Step 1: Extract basic profile
        profile = await self._extract_profile(resume_text, target_role)
        
        # Step 2: Generate comprehensive analysis
        analysis = await self._analyze_resume(resume_text, profile, target_role)
        profile.analysis = analysis
        
        return profile

    async def _extract_profile(self, resume_text: str, target_role: Optional[str] = None) -> ResumeProfile:
        """Extract basic profile information from resume."""
        config = genai_types.GenerateContentConfig(
            system_instruction=(
                "You are a resume parser. Extract skills, experience, projects, level, and summary "
                "from the provided resume text. Normalize skills to Title Case. "
                "Return strictly valid JSON matching the schema. Do NOT include the 'analysis' field."
            ),
            response_mime_type="application/json",
            response_schema=ResumeProfile,
        )
        prompt = f"Extract structured profile data from this resume.\n"
        if target_role:
            prompt += f"Target role: {target_role}\n"
        prompt += f"Resume:\n{resume_text}"

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Gemini returned no response for profile extraction")
        
        text = response.candidates[0].content.parts[0].text
        return self._parse_profile(text)

    async def _analyze_resume(
        self, resume_text: str, profile: ResumeProfile, target_role: Optional[str] = None
    ) -> ResumeAnalysis:
        """Generate comprehensive resume analysis with rating, feedback, and rewritten sections."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are an expert resume reviewer and career coach. Analyze the resume comprehensively.

Provide:
1. Rating (1-10) with detailed justification
2. Strengths as bullet points (what the resume does well)
3. Weaknesses as bullet points (areas lacking)
4. Mistakes found (grammar errors, formatting issues, ATS compliance problems, content clarity issues)
5. Specific improvement suggestions with examples
6. Skills/tools to add based on the candidate's domain
7. Overall summary in 4-6 lines
8. Professionally rewritten sections:
   - Summary: ATS-optimized, 3-4 lines, highlighting key value proposition
   - Skills: Well-organized with categories if applicable
   - Projects: Concise, impact-focused descriptions

Be specific and actionable in your feedback. Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=ResumeAnalysis,
        )
        
        skills_str = ", ".join(profile.skills) if profile.skills else "Not specified"
        projects_str = "\n".join([
            f"- {p.name}: {p.description or 'No description'}" 
            for p in profile.projects
        ]) if profile.projects else "No projects listed"
        
        prompt = f"""Analyze this resume and provide comprehensive feedback.

Target Role: {target_role or 'General'}
Candidate Level: {profile.level or 'Not specified'}
Current Skills: {skills_str}
Projects:
{projects_str}

Full Resume Text:
{resume_text}

Provide detailed analysis with rating, strengths, weaknesses, mistakes, suggestions, and professionally rewritten sections."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Gemini returned no response for resume analysis")
        
        text = response.candidates[0].content.parts[0].text
        return self._parse_analysis(text)

    def _parse_profile(self, payload: str) -> ResumeProfile:
        """Parse JSON response into ResumeProfile."""
        text = self._strip_markdown_fences(payload)
        try:
            data = json.loads(text)
            # Remove analysis if present (we'll add it separately)
            data.pop("analysis", None)
            return ResumeProfile(**data)
        except Exception as exc:
            raise RuntimeError(f"Failed to parse resume profile JSON: {text[:200]}") from exc

    def _parse_analysis(self, payload: str) -> ResumeAnalysis:
        """Parse JSON response into ResumeAnalysis."""
        text = self._strip_markdown_fences(payload)
        try:
            data = json.loads(text)
            return ResumeAnalysis(**data)
        except Exception as exc:
            raise RuntimeError(f"Failed to parse resume analysis JSON: {text[:200]}") from exc

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove markdown code fences if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines).strip()
        return text
