"""Pydantic models for job matching outputs."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    title: str = Field(description="Job title from SerpAPI result")
    company_name: str = Field(description="Company offering the job")
    location: str = Field(description="Job location")
    description: str = Field(description="Snippet or summary provided by the API")
    apply_link: str = Field(description="URL to apply")
    detected_skills: List[str] = Field(default_factory=list, description="Skills detected in the listing")


class JobMatch(BaseModel):
    posting: JobPosting
    match_score: float = Field(description="Match score between 0 and 1 inclusive")
    missing_skills: List[str] = Field(default_factory=list, description="Skills missing on the candidate profile")


class JobMatchResponse(BaseModel):
    matches: List[JobMatch] = Field(description="Ranked job matches")


# Job Recommendations (without real job postings)
class CompanyMatch(BaseModel):
    """A company recommendation based on profile."""
    company_type: str = Field(description="Type of company (e.g., 'AI Startup', 'Tech Giant', 'Consulting Firm')")
    reason: str = Field(description="Why this company type matches the candidate")
    example_companies: List[str] = Field(description="Example companies of this type")


class JobRecommendations(BaseModel):
    """AI-generated job recommendations based on resume."""
    recommended_roles: List[str] = Field(description="List of recommended job titles")
    matching_companies: List[CompanyMatch] = Field(description="Company types that match the profile")
    keywords_to_add: List[str] = Field(description="Keywords to add to resume for better matching")
    domain_fit: str = Field(description="Primary domain the candidate fits into")

