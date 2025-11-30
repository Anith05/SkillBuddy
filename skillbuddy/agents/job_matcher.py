"""Job matching agent orchestrated with Google ADK and SerpAPI."""
from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.function_tool import FunctionTool
from google.genai import Client
from google.genai import types as genai_types

from skillbuddy.config import google_api_key
from skillbuddy.services.serp import SerpApiClient, SerpApiQuotaExceeded
from skillbuddy.types.jobs import JobMatch, JobMatchResponse, JobPosting, JobRecommendations
from skillbuddy.types.profile import ResumeProfile

MODEL_ID = "gemini-flash-latest"
APP_NAME = "skillbuddy_job_matcher"
USER_ID = "matcher_user"
SESSION_ID = "matcher_session"


class JobMatcherAgent:
    """Calls SerpAPI via a tool and ranks results against the candidate profile."""

    def __init__(self) -> None:
        self._client = Client(api_key=google_api_key())
        self._serp = SerpApiClient()
        self._tool = FunctionTool(self._search_jobs)
        self._agent = Agent(
            model=MODEL_ID,
            name="job_matcher",
            description="Finds jobs aligned with validated skills and ranks them.",
            instruction=(
                "You evaluate candidate profiles and target roles. Always call the 'search_jobs' tool"
                " to retrieve up-to-date postings, then respond ONLY with JSON matching the JobMatchResponse"
                " schema. Include match_score between 0 and 1 and list missing skills per posting."
            ),
            tools=[self._tool],
        )

    def match_jobs(
        self,
        profile: ResumeProfile,
        target_role: str,
        location: Optional[str] = None,
        num_results: int = 5,
    ) -> List[JobMatch]:
        return asyncio.run(
            self.match_jobs_async(profile, target_role, location=location, num_results=num_results)
        )

    async def match_jobs_async(
        self,
        profile: ResumeProfile,
        target_role: str,
        location: Optional[str] = None,
        num_results: int = 5,
    ) -> List[JobMatch]:
        session_service = InMemorySessionService()
        _ = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
        runner = Runner(agent=self._agent, app_name=APP_NAME, session_service=session_service)

        prompt = self._build_prompt(profile, target_role, location, num_results)
        content = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])

        events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
        async for event in events:
            if event.is_final_response():
                if not event.content or not event.content.parts:
                    # Empty response from ADK, try direct call
                    return await self._direct_match(profile, target_role, location, num_results)
                payload = event.content.parts[0].text
                try:
                    return self._parse_matches(payload)
                except RuntimeError:
                    # Fallback: call Gemini directly with structured output
                    return await self._direct_match(profile, target_role, location, num_results)

        # No final response from ADK agent; try direct call
        return await self._direct_match(profile, target_role, location, num_results)

    async def _direct_match(
        self,
        profile: ResumeProfile,
        target_role: str,
        location: Optional[str],
        num_results: int,
    ) -> List[JobMatch]:
        """Fallback: search jobs and score with direct Gemini call."""
        # First get job postings from SerpAPI
        jobs_json = await self._search_jobs(target_role, location=location, num_results=num_results)
        jobs_data = json.loads(jobs_json)
        
        if not jobs_data:
            return []
        
        # Now ask Gemini to score them
        config = genai_types.GenerateContentConfig(
            system_instruction=(
                "You are a job matching assistant. Given a candidate profile and job postings, "
                "score each job 0-1 based on skill match and identify missing skills. "
                "Return strictly valid JSON matching the schema."
            ),
            response_mime_type="application/json",
            response_schema=JobMatchResponse,
        )
        
        skills = ", ".join(profile.skills)
        prompt = (
            f"Candidate skills: {skills}\n"
            f"Candidate summary: {profile.summary}\n"
            f"Target role: {target_role}\n\n"
            f"Job postings:\n{json.dumps(jobs_data, indent=2)}\n\n"
            "Score each job and identify missing skills."
        )
        
        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        # Check for valid response
        if not response.candidates:
            raise RuntimeError("Gemini returned no candidates for job matching")
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise RuntimeError("Gemini returned empty content for job matching")
        
        text = candidate.content.parts[0].text
        return self._parse_matches(text)

    def _build_prompt(
        self,
        profile: ResumeProfile,
        target_role: str,
        location: Optional[str],
        num_results: int,
    ) -> str:
        skills = ", ".join(profile.skills)
        summary = profile.summary or "No summary provided"
        role_line = f"Target role: {target_role}"
        location_line = f"Preferred location: {location}" if location else "Location flexible"
        request = (
            f"Candidate summary: {summary}\n"
            f"Skills: {skills}\n"
            f"Desired number of matches: {num_results}\n"
            f"{role_line}\n{location_line}\n"
            "Evaluate fit, penalize missing skills, and call 'search_jobs' using the target role and"
            " location context to obtain postings."
        )
        return request

    async def _search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        num_results: int = 10,
    ) -> str:
        try:
            payload = await self._serp.search_jobs(query=query, location=location, num_results=num_results)
        except SerpApiQuotaExceeded as exc:
            raise RuntimeError(str(exc)) from exc

        simplified: List[dict] = []
        for job in payload.get("jobs_results", []):
            apply_link = job.get("apply_link") or job.get("serpapi_link") or ""
            simplified.append(
                {
                    "title": job.get("title", ""),
                    "company_name": job.get("company_name", ""),
                    "location": job.get("location", ""),
                    "description": job.get("description")
                    or job.get("snippet")
                    or "",
                    "apply_link": apply_link,
                    "detected_skills": job.get("detected_extensions", {}).get("skills", []),
                }
            )
        return json.dumps(simplified)

    def _parse_matches(self, payload: str) -> List[JobMatch]:
        # Strip markdown code fences if present
        text = payload.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines).strip()
        
        try:
            data = json.loads(text)
            # Handle both {"matches": [...]} and direct [...] array
            if isinstance(data, list):
                data = {"matches": data}
            response = JobMatchResponse(**data)
            return response.matches
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to parse job match response JSON: {text[:200]}") from exc

    @property
    def remaining_quota(self) -> int:
        return self._serp.remaining_quota

    def get_job_recommendations(self, profile: ResumeProfile, target_role: str, location: Optional[str] = None) -> JobRecommendations:
        """Generate AI-based job recommendations without hallucinating specific postings."""
        config = genai_types.GenerateContentConfig(
            system_instruction="""You are a career advisor. Based on the candidate's resume, provide realistic job recommendations.

IMPORTANT RULES:
- Do NOT hallucinate specific job postings or URLs
- Only provide realistic job role titles and company TYPE mappings
- Base recommendations on actual skills, experience, and domain from the resume
- Be specific about why each recommendation matches

Provide:
1. Recommended Job Roles: 5-7 job titles that match their skills and experience level
2. Matching Company Types: Types of companies that would value their skills, with example companies
3. Keywords to Add: Resume keywords that would improve job matching in their domain
4. Domain Fit: Primary industry/domain they're best suited for

Return strictly valid JSON matching the schema.""",
            response_mime_type="application/json",
            response_schema=JobRecommendations,
        )
        
        skills = ", ".join(profile.skills) if profile.skills else "General programming"
        projects_info = "\n".join([
            f"- {p.name}: {p.description or 'No description'} (Tech: {', '.join(p.technologies) if p.technologies else 'Not specified'})"
            for p in profile.projects
        ]) if profile.projects else "No projects listed"
        
        experience_info = "\n".join([
            f"- {e.title} at {e.company or 'Unknown'} ({e.duration or 'Duration not specified'})"
            for e in profile.experience
        ]) if profile.experience else "No experience listed"

        prompt = f"""Generate job recommendations for this candidate.

Target Role: {target_role}
Preferred Location: {location or 'Flexible'}
Candidate Level: {profile.level or 'Not specified'}

Skills: {skills}

Projects:
{projects_info}

Experience:
{experience_info}

Summary: {profile.summary or 'Not provided'}

Provide realistic, well-matched job recommendations based on their actual qualifications."""

        response = self._client.models.generate_content(
            model=MODEL_ID,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=config,
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Failed to generate job recommendations")
        
        text = self._strip_markdown_fences(response.candidates[0].content.parts[0].text)
        data = json.loads(text)
        return JobRecommendations(**data)

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove markdown code fences if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines).strip()
        return text
