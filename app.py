"""Streamlit UI for the SkillBuddy career accelerator."""
from __future__ import annotations

from io import BytesIO
from typing import List, Optional

import streamlit as st

import skillbuddy.config as app_config
from skillbuddy.agents.interview_coach import InterviewCoach
from skillbuddy.agents.job_matcher import JobMatcherAgent
from skillbuddy.agents.resume_analyzer import ResumeAnalyzerAgent
from skillbuddy.config import ConfigError
from skillbuddy.types.interview import (
    InterviewQuestion, InterviewEvaluation, MCQQuiz,
    LiveInterviewQuestion, LiveInterviewResult
)
from skillbuddy.types.jobs import JobMatch, JobRecommendations
from skillbuddy.types.profile import ResumeProfile
from skillbuddy.utils.pdf_loader import extract_text_from_pdf


st.set_page_config(page_title="SkillBuddy", layout="wide")
st.title("🎯 SkillBuddy – Interview in Minutes")


def _apply_session_keys() -> None:
    if "google_api_key" in st.session_state:
        app_config.set_google_api_key(st.session_state.get("google_api_key"))
    if "serpapi_key" in st.session_state:
        app_config.set_serpapi_key(st.session_state.get("serpapi_key"))


_apply_session_keys()


# Sidebar for API Keys
with st.sidebar:
    st.header("⚙️ Configuration")
    with st.form("api_keys_form"):
        google_input = st.text_input(
            "Google API Key",
            value=st.session_state.get("google_api_key", ""),
            type="password",
            help="Used for Gemini API calls.",
        )
        serp_input = st.text_input(
            "SerpAPI Key",
            value=st.session_state.get("serpapi_key", ""),
            type="password",
            help="Used for Google Jobs searches.",
        )
        submitted = st.form_submit_button("Apply Keys")
        if submitted:
            st.session_state["google_api_key"] = google_input.strip()
            st.session_state["serpapi_key"] = serp_input.strip()
            app_config.set_google_api_key(google_input.strip() or None)
            app_config.set_serpapi_key(serp_input.strip() or None)
            st.success("API keys updated!")

    google_ready = True
    serp_ready = True
    try:
        if not st.session_state.get("google_api_key"):
            app_config.google_api_key()
    except ConfigError:
        google_ready = False

    try:
        if not st.session_state.get("serpapi_key"):
            app_config.serpapi_key()
    except ConfigError:
        serp_ready = False

    st.caption("✅ Google API ready" if google_ready else "⚠️ Google API key missing")
    st.caption("✅ SerpAPI ready" if serp_ready else "⚠️ SerpAPI key missing")

    st.session_state["__google_ready"] = google_ready
    st.session_state["__serp_ready"] = serp_ready


def _handle_api_error(exc: Exception, context: str) -> None:
    """Display user-friendly error messages for API errors."""
    message = str(exc)
    if "RESOURCE_EXHAUSTED" in message:
        st.error(f"{context}: Gemini API quota exceeded. Please wait and try again.")
    elif "INTERNAL" in message or "500" in message:
        st.error(f"{context}: Gemini API internal error. Please try again in a few seconds.")
    else:
        st.error(f"{context}: {message}")


# =====================
# SECTION 1: RESUME UPLOAD & ANALYSIS
# =====================
st.markdown("## 📄 1. Resume Analysis")

with st.expander("Upload & Analyze Resume", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        target_role = st.text_input("🎯 Target Role", value="Software Engineer")
    with col2:
        job_location = st.text_input("📍 Preferred Location (optional)")
    
    google_ready = st.session_state.get("__google_ready", False)
    serp_ready = st.session_state.get("__serp_ready", False)
    
    resume_file = st.file_uploader("Upload your resume PDF", type=["pdf"])
    
    analyze_clicked = st.button(
        "🔍 Analyze Resume",
        disabled=(resume_file is None or not google_ready),
        help=None if google_ready else "Provide a Google API key first.",
        type="primary",
    )

    if analyze_clicked and resume_file:
        with st.spinner("Analyzing your resume..."):
            try:
                resume_bytes = resume_file.read()
                resume_text = extract_text_from_pdf(BytesIO(resume_bytes))
                analyzer = ResumeAnalyzerAgent()
                profile = analyzer.analyze(resume_text, target_role=target_role)
                st.session_state["resume_profile"] = profile
                # Reset interview state when new resume is uploaded
                for key in ["live_interview_started", "live_questions", "live_answers", 
                           "live_current_q", "live_result", "interview_questions",
                           "interview_answers", "interview_evaluation", "mcq_quiz",
                           "quiz_answers", "show_quiz_results", "job_matches", "job_recommendations"]:
                    st.session_state.pop(key, None)
                st.success("✅ Resume analyzed successfully!")
            except ConfigError as cfg_err:
                st.error(str(cfg_err))
            except Exception as exc:
                _handle_api_error(exc, "Resume analysis failed")

profile: Optional[ResumeProfile] = st.session_state.get("resume_profile")

# Display resume analysis
if profile and profile.analysis:
    analysis = profile.analysis
    
    st.markdown("### 📊 Resume Rating")
    col1, col2 = st.columns([1, 3])
    with col1:
        rating_color = "🟢" if analysis.rating >= 7 else "🟡" if analysis.rating >= 5 else "🔴"
        st.markdown(f"# {rating_color} {analysis.rating}/10")
    with col2:
        st.text_area("Rating Justification", value=analysis.rating_justification, height=80, disabled=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ✅ Strengths")
        strengths_text = "\n".join([f"• {s}" for s in analysis.strengths]) if analysis.strengths else "No strengths identified"
        st.text_area("Strengths", value=strengths_text, height=150, disabled=True, label_visibility="collapsed")
    
    with col2:
        st.markdown("### ⚠️ Weaknesses")
        weaknesses_text = "\n".join([f"• {w}" for w in analysis.weaknesses]) if analysis.weaknesses else "No weaknesses identified"
        st.text_area("Weaknesses", value=weaknesses_text, height=150, disabled=True, label_visibility="collapsed")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ❌ Mistakes Found")
        mistakes_text = "\n".join([f"• {m}" for m in analysis.mistakes]) if analysis.mistakes else "No mistakes found"
        st.text_area("Mistakes", value=mistakes_text, height=150, disabled=True, label_visibility="collapsed")
    
    with col2:
        st.markdown("### 💡 Suggestions")
        suggestions_text = "\n".join([f"• {s}" for s in analysis.suggestions]) if analysis.suggestions else "No suggestions"
        st.text_area("Suggestions", value=suggestions_text, height=150, disabled=True, label_visibility="collapsed")
    
    st.markdown("---")
    
    st.markdown("### 🛠️ Recommended Skills to Add")
    skills_to_add = ", ".join(analysis.skills_to_add) if analysis.skills_to_add else "No additional skills recommended"
    st.text_area("Skills to Add", value=skills_to_add, height=68, disabled=True, label_visibility="collapsed")
    
    st.markdown("### 📝 Overall Summary")
    st.text_area("Summary", value=analysis.overall_summary, height=120, disabled=True, label_visibility="collapsed")
    
    st.markdown("---")
    
    st.markdown("### ✨ Professionally Rewritten Sections")
    with st.expander("📋 Rewritten Summary"):
        st.text_area("New Summary", value=analysis.rewritten.summary, height=100, disabled=True, label_visibility="collapsed")
    with st.expander("🛠️ Rewritten Skills"):
        st.text_area("New Skills", value=analysis.rewritten.skills, height=100, disabled=True, label_visibility="collapsed")
    with st.expander("🚀 Rewritten Projects"):
        for i, proj in enumerate(analysis.rewritten.projects):
            st.text_area(f"Project {i+1}", value=proj, height=80, disabled=True, key=f"rewritten_proj_{i}")

    # =====================
    # PROMPT FOR LIVE INTERVIEW
    # =====================
    st.markdown("---")
    st.markdown("### 🎤 Would you like to start the Live Mock Interview?")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎙️ Yes, with Voice (Mic)", type="primary", disabled=not google_ready):
            st.session_state["live_interview_started"] = True
            st.session_state["live_mode"] = "audio"
            st.session_state["live_current_q"] = 0
            st.session_state["live_answers"] = []
            st.session_state["live_transcripts"] = []
            st.rerun()
    with col2:
        if st.button("⌨️ Yes, Text-based", disabled=not google_ready):
            st.session_state["live_interview_started"] = True
            st.session_state["live_mode"] = "text"
            st.session_state["live_current_q"] = 0
            st.session_state["live_answers"] = []
            st.rerun()
    with col3:
        if st.button("📝 No, Standard Q&A Mode"):
            st.session_state["live_interview_started"] = False
            st.session_state["use_standard_mode"] = True
            st.rerun()


# =====================
# SECTION 2: LIVE MOCK INTERVIEW MODE
# =====================
if profile and st.session_state.get("live_interview_started"):
    st.markdown("---")
    st.markdown("## 🎤 2. Live Mock Interview")
    
    live_mode = st.session_state.get("live_mode", "text")
    
    if live_mode == "audio":
        st.info("🎙️ **Voice Mode**: Record your answer using the microphone, then click Submit. If mic doesn't work, you can switch to text mode.")
    else:
        st.info("⌨️ **Text Mode**: Type your answer and click Submit to proceed.")
    
    # Mode switch button
    if live_mode == "audio":
        if st.button("⌨️ Switch to Text Mode"):
            st.session_state["live_mode"] = "text"
            st.rerun()
    else:
        if st.button("🎙️ Switch to Voice Mode"):
            st.session_state["live_mode"] = "audio"
            st.rerun()
    
    coach = InterviewCoach()
    
    # Generate questions if not already done
    if "live_questions" not in st.session_state:
        with st.spinner("Preparing interview questions..."):
            try:
                questions = coach.generate_live_interview_questions(profile, target_role or "Software Engineer")
                st.session_state["live_questions"] = questions
                st.session_state["live_answers"] = []
                st.session_state["live_transcripts"] = []
                st.session_state["live_current_q"] = 0
            except Exception as exc:
                _handle_api_error(exc, "Failed to generate questions")
                st.session_state["live_interview_started"] = False
                st.rerun()
    
    questions: List[LiveInterviewQuestion] = st.session_state.get("live_questions", [])
    answers: List[str] = st.session_state.get("live_answers", [])
    transcripts: List[str] = st.session_state.get("live_transcripts", [])
    current_q: int = st.session_state.get("live_current_q", 0)
    
    if questions and current_q < len(questions):
        q = questions[current_q]
        
        # Show progress
        st.progress((current_q) / len(questions), text=f"Question {current_q + 1} of {len(questions)}")
        
        # Show category badge
        category_labels = {
            "intro": "🙋 Introduction",
            "project": "🚀 Project",
            "technical": "💻 Technical",
            "problem_solving": "🧩 Problem Solving",
            "hr_culture": "🤝 HR/Culture"
        }
        st.markdown(f"**{category_labels.get(q.category, q.category)}**")
        
        # Show question
        st.markdown(f"### Q{q.question_number}: {q.question}")
        
        # Answer input based on mode
        answer = ""
        audio_bytes = None
        
        if live_mode == "audio":
            # Audio recording section
            st.markdown("#### 🎙️ Record Your Answer")
            
            uploaded_audio = st.file_uploader(
                "Upload audio file or record using your device",
                type=["wav", "mp3", "m4a", "webm", "ogg"],
                key=f"audio_upload_{current_q}",
                help="Record using your device's voice recorder app and upload, or use the audio recorder below."
            )
            
            # Try to use audio_recorder if available
            try:
                from audio_recorder_streamlit import audio_recorder
                st.markdown("**Or record directly:**")
                recorded_audio = audio_recorder(
                    text="Click to record",
                    recording_color="#e74c3c",
                    neutral_color="#3498db",
                    key=f"recorder_{current_q}"
                )
                if recorded_audio:
                    audio_bytes = recorded_audio
                    st.audio(audio_bytes, format="audio/wav")
            except ImportError:
                st.caption("💡 Tip: Install `audio-recorder-streamlit` for in-browser recording: `pip install audio-recorder-streamlit`")
            
            if uploaded_audio:
                audio_bytes = uploaded_audio.read()
                st.audio(audio_bytes)
            
            # Also show text input as backup
            st.markdown("**Or type your answer:**")
            answer = st.text_area(
                "Text Answer (optional)",
                height=100,
                key=f"live_answer_{current_q}",
                placeholder="Type here if you prefer text or if mic doesn't work..."
            )
            
            can_submit = bool(audio_bytes) or bool(answer.strip())
            
        else:
            # Text mode
            answer = st.text_area(
                "Your Answer",
                height=150,
                key=f"live_answer_{current_q}",
                placeholder="Type your answer here... Be specific and use examples from your experience."
            )
            can_submit = bool(answer.strip())
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Submit Answer", type="primary", disabled=not can_submit):
                with st.spinner("Processing..."):
                    try:
                        final_answer = ""
                        
                        # Process audio if available
                        if audio_bytes and live_mode == "audio":
                            try:
                                # Determine mime type
                                mime_type = "audio/wav"
                                if uploaded_audio:
                                    name = uploaded_audio.name.lower()
                                    if name.endswith(".mp3"):
                                        mime_type = "audio/mp3"
                                    elif name.endswith(".m4a"):
                                        mime_type = "audio/m4a"
                                    elif name.endswith(".webm"):
                                        mime_type = "audio/webm"
                                    elif name.endswith(".ogg"):
                                        mime_type = "audio/ogg"
                                
                                # Transcribe audio
                                transcript = coach.transcribe_audio(audio_bytes, mime_type)
                                st.success(f"📝 Transcribed: {transcript}")
                                final_answer = transcript
                                transcripts.append(transcript)
                                st.session_state["live_transcripts"] = transcripts
                            except Exception as e:
                                st.warning(f"Could not transcribe audio: {e}. Using text input if available.")
                                if answer.strip():
                                    final_answer = answer
                                else:
                                    st.error("Please provide a text answer or try recording again.")
                                    st.stop()
                        else:
                            final_answer = answer
                        
                        # Check answer clarity
                        feedback = coach.check_answer_clarity(q.question, final_answer, profile)
                        
                        if feedback.needs_clarification and feedback.clarification_prompt:
                            st.warning(f"💡 {feedback.clarification_prompt}")
                        else:
                            # Accept answer and move to next
                            answers.append(final_answer)
                            st.session_state["live_answers"] = answers
                            st.session_state["live_current_q"] = current_q + 1
                            
                            if feedback.brief_feedback:
                                st.success(f"✓ {feedback.brief_feedback}")
                            
                            st.rerun()
                    except Exception as exc:
                        # Just accept the answer and move on
                        if final_answer:
                            answers.append(final_answer)
                        elif answer.strip():
                            answers.append(answer)
                        else:
                            answers.append("[Error processing answer]")
                        st.session_state["live_answers"] = answers
                        st.session_state["live_current_q"] = current_q + 1
                        st.rerun()
        
        with col2:
            if st.button("Skip Question"):
                answers.append("[Skipped]")
                st.session_state["live_answers"] = answers
                st.session_state["live_current_q"] = current_q + 1
                st.rerun()
    
    elif questions and current_q >= len(questions):
        # Interview complete - show evaluation
        st.markdown("### 🎉 Interview Complete!")
        
        if "live_result" not in st.session_state:
            with st.spinner("Evaluating your interview..."):
                try:
                    result = coach.evaluate_live_interview(questions, answers, profile)
                    st.session_state["live_result"] = result
                except Exception as exc:
                    _handle_api_error(exc, "Evaluation failed")
        
        result: Optional[LiveInterviewResult] = st.session_state.get("live_result")
        
        if result:
            # Display results
            col1, col2 = st.columns(2)
            with col1:
                score_color = "🟢" if result.interview_score >= 7 else "🟡" if result.interview_score >= 5 else "🔴"
                st.markdown(f"### 🎤 Interview Score: {score_color} {result.interview_score}/10")
            with col2:
                comm_color = "🟢" if result.communication_score >= 7 else "🟡" if result.communication_score >= 5 else "🔴"
                st.markdown(f"### 🗣️ Communication Score: {comm_color} {result.communication_score}/10")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 💪 Strengths in Answering")
                for s in result.strengths_in_answering:
                    st.write(f"• {s}")
            with col2:
                st.markdown("### 🧠 Improvement Areas")
                for i in result.improvement_areas:
                    st.write(f"• {i}")
            
            st.markdown("---")
            
            st.markdown("### 📍 Weak Points Identified")
            weak_points = ", ".join(result.weak_points) if result.weak_points else "None identified"
            st.text_area("Weak Points", value=weak_points, height=68, disabled=True, label_visibility="collapsed")
            
            st.markdown("### 📘 Suggestions to Improve")
            suggestions = "\n".join([f"• {s}" for s in result.suggestions]) if result.suggestions else "No suggestions"
            st.text_area("Suggestions", value=suggestions, height=120, disabled=True, label_visibility="collapsed")
            
            # Ask about quiz
            st.markdown("---")
            st.markdown("### 🧠 Would you like a short quiz based on your skills?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Start Quiz", type="primary"):
                    st.session_state["show_mcq_quiz"] = True
                    st.rerun()
            with col2:
                if st.button("⏭️ Skip to Job Matcher"):
                    st.session_state["show_job_matcher"] = True
                    st.rerun()


# =====================
# SECTION 2 (ALTERNATIVE): STANDARD Q&A MODE
# =====================
if profile and st.session_state.get("use_standard_mode") and not st.session_state.get("live_interview_started"):
    st.markdown("---")
    st.markdown("## 🎤 2. Mock Interview Coach (Standard Mode)")
    
    coach = InterviewCoach()
    questions: List[InterviewQuestion] = st.session_state.get("interview_questions", [])
    
    if not questions:
        if st.button("🎯 Generate Interview Questions", type="primary", disabled=not google_ready):
            with st.spinner("Generating questions..."):
                try:
                    questions = coach.generate_questions(profile, target_role or "Software Engineer")
                    st.session_state["interview_questions"] = questions
                    st.session_state["interview_answers"] = [""] * len(questions)
                    st.rerun()
                except Exception as exc:
                    _handle_api_error(exc, "Question generation failed")
    
    if questions:
        st.info("Answer each question below. Be specific and use examples.")
        
        answers = st.session_state.get("interview_answers", [""] * len(questions))
        
        for i, q in enumerate(questions):
            st.markdown(f"**Q{i+1} ({q.category.replace('_', ' ').title()}):** {q.question}")
            answers[i] = st.text_area(
                f"Answer {i+1}",
                value=answers[i],
                height=120,
                key=f"std_answer_{i}",
                placeholder="Type your answer here...",
                label_visibility="collapsed",
            )
        
        st.session_state["interview_answers"] = answers
        
        all_answered = all(a.strip() for a in answers)
        
        if st.button("✅ Submit & Evaluate", disabled=not all_answered, type="primary"):
            with st.spinner("Evaluating..."):
                try:
                    evaluation = coach.evaluate_answers(questions, answers, profile)
                    st.session_state["interview_evaluation"] = evaluation
                    st.rerun()
                except Exception as exc:
                    _handle_api_error(exc, "Evaluation failed")
        
        # Display evaluation if available
        evaluation: Optional[InterviewEvaluation] = st.session_state.get("interview_evaluation")
        if evaluation:
            st.markdown("---")
            st.markdown("### 📊 Interview Evaluation")
            
            score_color = "🟢" if evaluation.overall_score >= 7 else "🟡" if evaluation.overall_score >= 5 else "🔴"
            st.markdown(f"## Overall Score: {score_color} {evaluation.overall_score}/10")
            
            for eval_item in evaluation.evaluations:
                with st.expander(f"Q{eval_item.question_number} - Score: {eval_item.score}/10"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**✅ Strengths:**")
                        for s in eval_item.strengths:
                            st.write(f"• {s}")
                    with col2:
                        st.markdown("**📈 Improvements:**")
                        for imp in eval_item.improvements:
                            st.write(f"• {imp}")
            
            # Soft skills
            st.markdown("#### 🗣️ Soft Skills")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Communication", f"{evaluation.soft_skills.communication_clarity}/10")
            with col2:
                st.metric("Structure", f"{evaluation.soft_skills.structure}/10")
            with col3:
                st.metric("Confidence", f"{evaluation.soft_skills.confidence}/10")


# =====================
# SECTION 3: MCQ QUIZ
# =====================
if profile and (st.session_state.get("show_mcq_quiz") or st.session_state.get("use_standard_mode")):
    st.markdown("---")
    st.markdown("## 🧠 3. Technical Quiz")
    
    coach = InterviewCoach()
    quiz: Optional[MCQQuiz] = st.session_state.get("mcq_quiz")
    
    if not quiz:
        if st.button("📝 Generate MCQ Quiz", disabled=not google_ready):
            with st.spinner("Generating quiz..."):
                try:
                    quiz = coach.generate_mcq_quiz(profile)
                    st.session_state["mcq_quiz"] = quiz
                    st.session_state["quiz_answers"] = {}
                    st.session_state["show_quiz_results"] = False
                    st.rerun()
                except Exception as exc:
                    _handle_api_error(exc, "Quiz generation failed")
    
    if quiz:
        quiz_answers = st.session_state.get("quiz_answers", {})
        
        for q in quiz.questions:
            st.markdown(f"**Q{q.question_number}:** {q.question}")
            options = [f"{opt.label}. {opt.text}" for opt in q.options]
            
            current_idx = None
            if q.question_number in quiz_answers:
                try:
                    current_idx = options.index(quiz_answers[q.question_number])
                except ValueError:
                    current_idx = None
            
            selected = st.radio(
                f"Q{q.question_number}",
                options=options,
                key=f"mcq_{q.question_number}",
                index=current_idx,
                label_visibility="collapsed",
            )
            if selected:
                quiz_answers[q.question_number] = selected
            st.markdown("---")
        
        st.session_state["quiz_answers"] = quiz_answers
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Check Answers", type="primary"):
                st.session_state["show_quiz_results"] = True
                st.rerun()
        with col2:
            if st.button("🔄 New Quiz"):
                st.session_state.pop("mcq_quiz", None)
                st.session_state.pop("quiz_answers", None)
                st.session_state.pop("show_quiz_results", None)
                st.rerun()
        
        if st.session_state.get("show_quiz_results"):
            st.markdown("### 📊 Quiz Results")
            correct_count = 0
            for q in quiz.questions:
                user_answer = quiz_answers.get(q.question_number, "")
                user_label = user_answer[0] if user_answer else ""
                is_correct = user_label == q.correct_answer
                if is_correct:
                    correct_count += 1
                
                status = "✅" if is_correct else "❌"
                st.markdown(f"**Q{q.question_number}:** {status} Your answer: {user_label or 'Not answered'} | Correct: {q.correct_answer}")
                st.caption(f"💡 {q.explanation}")
            
            st.markdown(f"### Score: {correct_count}/{len(quiz.questions)}")


# =====================
# SECTION 4: JOB MATCHER
# =====================
if profile and (st.session_state.get("show_job_matcher") or st.session_state.get("live_result") or st.session_state.get("use_standard_mode")):
    st.markdown("---")
    st.markdown("## 💼 4. Job Matcher")
    
    matcher = JobMatcherAgent()
    
    # AI Recommendations (no API needed for SerpAPI)
    st.markdown("### 🎯 AI Job Recommendations")
    
    recommendations: Optional[JobRecommendations] = st.session_state.get("job_recommendations")
    
    if not recommendations:
        if st.button("🔍 Get Job Recommendations", type="primary", disabled=not google_ready):
            with st.spinner("Analyzing your profile for job matches..."):
                try:
                    recommendations = matcher.get_job_recommendations(profile, target_role or "Software Engineer", job_location)
                    st.session_state["job_recommendations"] = recommendations
                    st.rerun()
                except Exception as exc:
                    _handle_api_error(exc, "Failed to get recommendations")
    
    if recommendations:
        st.markdown(f"**🌐 Domain Fit:** {recommendations.domain_fit}")
        
        st.markdown("### 🏢 Recommended Job Roles")
        for role in recommendations.recommended_roles:
            st.write(f"• {role}")
        
        st.markdown("### 🎯 Matching Company Types")
        for company in recommendations.matching_companies:
            with st.expander(f"**{company.company_type}**"):
                st.write(f"**Why it matches:** {company.reason}")
                st.write(f"**Examples:** {', '.join(company.example_companies)}")
        
        st.markdown("### 📍 Keywords to Add for Better Matching")
        keywords = ", ".join(recommendations.keywords_to_add) if recommendations.keywords_to_add else "None suggested"
        st.text_area("Keywords", value=keywords, height=68, disabled=True, label_visibility="collapsed")
    
    # Real Job Search (requires SerpAPI)
    st.markdown("---")
    st.markdown("### 🔎 Search Real Job Postings")
    
    job_results: List[JobMatch] = st.session_state.get("job_matches", [])
    
    if st.button("🔍 Find Matching Jobs", disabled=not serp_ready, help="Requires SerpAPI key"):
        with st.spinner("Searching jobs..."):
            try:
                matches = matcher.match_jobs(
                    profile=profile,
                    target_role=target_role or "Software Engineer",
                    location=job_location or None,
                    num_results=5,
                )
                st.session_state["job_matches"] = matches
                job_results = matches
            except Exception as exc:
                _handle_api_error(exc, "Job search failed")

    if job_results:
        st.markdown("### 🎯 Top Matching Jobs")
        for match in job_results:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{match.posting.title}** at {match.posting.company_name}")
                    st.caption(f"📍 {match.posting.location}")
                with col2:
                    match_pct = int(match.match_score * 100)
                    color = "🟢" if match_pct >= 70 else "🟡" if match_pct >= 50 else "🔴"
                    st.markdown(f"### {color} {match_pct}%")
                
                st.text_area(
                    "Description",
                    value=match.posting.description,
                    height=100,
                    disabled=True,
                    key=f"job_{match.posting.title}_{match.posting.company_name}",
                    label_visibility="collapsed",
                )
                
                if match.posting.apply_link:
                    st.link_button("Apply Now →", match.posting.apply_link)
                
                if match.missing_skills:
                    st.warning(f"📚 Skills to develop: {', '.join(match.missing_skills)}")
                
                st.markdown("---")
        
        st.caption(f"SerpAPI quota remaining: {matcher.remaining_quota}")


# Show info message if no profile yet
if not profile:
    st.info("👆 Upload and analyze your resume to get started!")
