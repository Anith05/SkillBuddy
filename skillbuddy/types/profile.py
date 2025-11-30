"""Pydantic models describing resume-derived user profile."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ExperienceItem(BaseModel):
    title: str = Field(description="Role title extracted from the resume")
    company: Optional[str] = Field(default=None, description="Company or organization name")
    duration: Optional[str] = Field(default=None, description="Duration string as reported")
    highlights: List[str] = Field(default_factory=list, description="Bullet highlights")


class ProjectItem(BaseModel):
    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None, description="Short project overview")
    technologies: List[str] = Field(default_factory=list, description="Tech stack keywords")


class RewrittenSections(BaseModel):
    """Professionally rewritten resume sections."""
    summary: str = Field(description="ATS-optimized professional summary in 3-4 lines")
    skills: str = Field(description="Well-organized skills section with categories")
    projects: List[str] = Field(default_factory=list, description="Rewritten project descriptions")


class ResumeAnalysis(BaseModel):
    """Comprehensive resume analysis with rating and feedback."""
    rating: int = Field(ge=1, le=10, description="Overall resume rating 1-10")
    rating_justification: str = Field(description="Explanation for the rating")
    strengths: List[str] = Field(default_factory=list, description="Resume strengths as bullet points")
    weaknesses: List[str] = Field(default_factory=list, description="Resume weaknesses as bullet points")
    mistakes: List[str] = Field(default_factory=list, description="Grammar, formatting, ATS compliance issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions with examples")
    skills_to_add: List[str] = Field(default_factory=list, description="Recommended skills/tools based on domain")
    overall_summary: str = Field(description="4-6 line overall resume summary")
    rewritten: RewrittenSections = Field(description="Professionally rewritten sections")


class ResumeProfile(BaseModel):
    skills: List[str] = Field(default_factory=list, description="Normalized skills claimed in the resume")
    experience: List[ExperienceItem] = Field(default_factory=list, description="Experience entries")
    projects: List[ProjectItem] = Field(default_factory=list, description="Projects and portfolio items")
    level: Optional[str] = Field(default=None, description="Seniority level estimated by analyzer")
    summary: Optional[str] = Field(default=None, description="One sentence snapshot of candidate strengths")
    analysis: Optional[ResumeAnalysis] = Field(default=None, description="Detailed resume analysis")
