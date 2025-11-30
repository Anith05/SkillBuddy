# SkillBuddy – 10-Minute Career Accelerator

SkillBuddy is a Streamlit application that compresses the job preparation workflow into three AI-powered agents built with the Google Agent Development Kit (ADK):

1. **The Analyzer** – parses your PDF resume, extracts structured skills and experience, and stores a validated profile in session state.
2. **The Coach** – generates resume-aware interview questions, records browser audio, and evaluates answers with Gemini multimodal feedback.
3. **The Matcher** – calls SerpAPI Google Jobs search, ranks postings against validated skills, and returns match percentages.

## Features
- PyPDF resume ingestion with structured JSON output powered by Gemini and ADK tools
- Browser-based audio recording through `streamlit-webrtc` plus fallback audio uploads
- Multimodal coaching feedback (content, communication, visual cues) in JSON schema
- SerpAPI Google Jobs integration with quota-aware caching and LLM ranking
- `.env` configuration for API keys and Streamlit session-only persistence

## Project Layout
```
app.py                         # Streamlit UI orchestrating the three agents
skillbuddy/
  agents/
    resume_analyzer.py         # ADK agent converting resume text into ResumeProfile
    interview_coach.py         # Question generation and multimodal evaluation
    job_matcher.py             # ADK agent calling SerpAPI and ranking matches
  services/
    serp.py                    # SerpAPI client with caching and quota tracking
  types/
    profile.py                 # Pydantic schema for resume-derived profile
    interview.py               # Pydantic schema for interview feedback
    jobs.py                    # Pydantic schema for job matches
  utils/
    pdf_loader.py              # PDF text extraction helper
config.py                      # Environment loading helpers (.env support)
```

## Getting Started
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys**
   - Copy `.env.example` to `.env`
   - Fill in `GOOGLE_API_KEY` and `SERPAPI_KEY`

3. **Run Streamlit**
   ```bash
   streamlit run app.py
   ```

4. **Workflow**
   - Upload a PDF resume and set your target role/location
   - Generate the tailored interview question and record your answer
   - Review feedback and request matched job listings

## Notes
- SerpAPI calls are cached for an hour to stay within the 250 requests/month limit.
- Only validated profile data persists, scoped to the current Streamlit session.
- The Live API-inspired audio loop leverages `streamlit-webrtc`; if unavailable, upload an audio file as a fallback.
