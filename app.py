"""PrepAIr - CV Matching & Improvement Streamlit App."""

import streamlit as st
import os
from services.pdf_extract import extract_pdf_text
from services.cv_structurer import structure_cv
from services.jd_structurer import structure_jd
from services.scoring import compute_match_score
from services.suggestions import generate_suggestions, locate_anchor_span, apply_suggestion
from services.docx_export import export_cv_to_docx


# Page config
st.set_page_config(
    page_title="PrepAIr - CV Matching & Improvement",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if "cv_text" not in st.session_state:
    st.session_state.cv_text = None
if "jd_text" not in st.session_state:
    st.session_state.jd_text = None
if "cv_data" not in st.session_state:
    st.session_state.cv_data = None
if "jd_data" not in st.session_state:
    st.session_state.jd_data = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "accepted_suggestions" not in st.session_state:
    st.session_state.accepted_suggestions = set()
if "ignored_suggestions" not in st.session_state:
    st.session_state.ignored_suggestions = set()
if "confirmed_suggestions" not in st.session_state:
    st.session_state.confirmed_suggestions = set()
if "improved_cv_text" not in st.session_state:
    st.session_state.improved_cv_text = None
if "final_cv_text" not in st.session_state:
    st.session_state.final_cv_text = None
if "current_score" not in st.session_state:
    st.session_state.current_score = 0
if "selected_suggestion_id" not in st.session_state:
    st.session_state.selected_suggestion_id = None


def highlight_text_with_span(text: str, start: int, end: int) -> str:
    """Create HTML with highlighted span."""
    if start >= end or start < 0 or end > len(text):
        return text.replace('\n', '<br>')
    
    before = text[:start].replace('\n', '<br>')
    highlight = text[start:end].replace('\n', '<br>')
    after = text[end:].replace('\n', '<br>')
    
    return f"{before}<span style='background-color: yellow; padding: 2px;'>{highlight}</span>{after}"


def main():
    st.title("📄 PrepAIr - CV Matching & Improvement")
    st.markdown("Upload your CV and paste a job description to get personalized improvement suggestions.")
    
    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        st.error("⚠️ GEMINI_API_KEY environment variable not set. Please set it in Replit Secrets or your environment.")
        st.stop()
    
    # Top section: Upload and JD input
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Upload CV (PDF)")
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="cv_uploader")
        
        if uploaded_file is not None:
            try:
                with st.spinner("Extracting text from PDF..."):
                    cv_text = extract_pdf_text(uploaded_file)
                    st.session_state.cv_text = cv_text
                    st.session_state.improved_cv_text = cv_text  # Initialize improved version
                    st.success(f"✅ PDF extracted successfully ({len(cv_text)} characters)")
                    st.text_area("Preview (first 500 chars):", cv_text[:500], height=100, disabled=True)
            except ValueError as e:
                st.error(f"❌ {str(e)}")
                st.session_state.cv_text = None
    
    with col2:
        st.subheader("2. Paste Job Description")
        jd_text = st.text_area(
            "Job Description",
            value=st.session_state.jd_text or "",
            height=200,
            key="jd_input",
            placeholder="Paste the job description here..."
        )
        st.session_state.jd_text = jd_text if jd_text else None
    
    st.divider()
    
    # Analysis button
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
    
    with col_btn1:
        analyze_clicked = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    with col_btn2:
        improve_clicked = st.button("✨ Improve CV", use_container_width=True, disabled=st.session_state.analysis is None)
    
    with col_btn3:
        save_clicked = st.button("💾 Save Version", use_container_width=True, disabled=st.session_state.improved_cv_text is None)
    
    with col_btn4:
        download_clicked = st.button("📥 Download DOCX", use_container_width=True, disabled=st.session_state.final_cv_text is None)
    
    # Handle Analyze button
    if analyze_clicked:
        if not st.session_state.cv_text:
            st.error("❌ Please upload a CV first.")
        elif not st.session_state.jd_text:
            st.error("❌ Please paste a job description.")
        else:
            with st.spinner("Analyzing CV and Job Description..."):
                try:
                    # Structure CV and JD
                    st.session_state.cv_data = structure_cv(st.session_state.cv_text)
                    st.session_state.jd_data = structure_jd(st.session_state.jd_text)
                    
                    # Compute match score
                    st.session_state.analysis = compute_match_score(
                        st.session_state.cv_data,
                        st.session_state.jd_data,
                        st.session_state.cv_text
                    )
                    st.session_state.current_score = st.session_state.analysis["match"]["score"]
                    
                    # Reset improvement state
                    st.session_state.suggestions = []
                    st.session_state.accepted_suggestions = set()
                    st.session_state.ignored_suggestions = set()
                    st.session_state.confirmed_suggestions = set()
                    st.session_state.improved_cv_text = st.session_state.cv_text
                    
                    st.success("✅ Analysis complete!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
    
    # Handle Improve CV button
    if improve_clicked:
        if not st.session_state.analysis:
            st.error("❌ Please run analysis first.")
        else:
            with st.spinner("Generating improvement suggestions..."):
                try:
                    # Add missing info to jd_data for suggestions
                    if "missing_required" not in st.session_state.jd_data:
                        jd_copy = st.session_state.jd_data.copy()
                        jd_copy["missing_required"] = st.session_state.analysis.get("missing_required", [])
                        jd_copy["missing_preferred"] = st.session_state.analysis.get("missing_preferred", [])
                    else:
                        jd_copy = st.session_state.jd_data
                    
                    suggestions = generate_suggestions(
                        st.session_state.improved_cv_text,
                        st.session_state.cv_data,
                        jd_copy,
                        st.session_state.current_score
                    )
                    st.session_state.suggestions = suggestions
                    st.success(f"✅ Generated {len(suggestions)} suggestions!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to generate suggestions: {str(e)}")
    
    # Handle Save Version button
    if save_clicked:
        st.session_state.final_cv_text = st.session_state.improved_cv_text
        st.success("✅ CV version saved as Final!")
        st.rerun()
    
    # Handle Download DOCX button
    if download_clicked:
        try:
            docx_bytes = export_cv_to_docx(st.session_state.final_cv_text)
            st.download_button(
                label="⬇️ Download Final CV as DOCX",
                data=docx_bytes,
                file_name="improved_cv.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"❌ Export failed: {str(e)}")
    
    # Display Analysis Results
    if st.session_state.analysis:
        st.divider()
        st.header("📊 Analysis Results")
        
        match = st.session_state.analysis["match"]
        score = match["score"]
        label = match["label"]
        
        # Score display
        col_score1, col_score2 = st.columns([3, 1])
        with col_score1:
            st.progress(score / 100, text=f"Match Score: {score}/100 - {label.upper()}")
        with col_score2:
            st.metric("Score", f"{score}/100")
        
        # Breakdown
        with st.expander("Score Breakdown"):
            breakdown = match["breakdown"]
            st.write(f"**Required Skills:** {breakdown['required_skills_score']:.1f}%")
            st.write(f"**Preferred Skills:** {breakdown['preferred_skills_score']:.1f}%")
            st.write(f"**Responsibilities:** {breakdown['responsibilities_score']:.1f}%")
            st.write(f"**Seniority Alignment:** {breakdown['seniority_alignment']:.1f}%")
        
        # Soft skills, strengths, gaps
        col_soft, col_str, col_gaps = st.columns(3)
        
        with col_soft:
            st.subheader("🎯 Soft Skill Focus")
            for skill in st.session_state.analysis.get("soft_skill_focus", []):
                st.chip(skill)
        
        with col_str:
            st.subheader("✅ Strengths")
            for strength in st.session_state.analysis.get("strengths", []):
                st.write(f"• {strength}")
        
        with col_gaps:
            st.subheader("⚠️ Gaps")
            for gap in st.session_state.analysis.get("gaps", []):
                st.write(f"• {gap}")
        
        st.info(f"💡 **Simulation Plan:** {st.session_state.analysis.get('simulation_plan', 'N/A')}")
    
    # Display Improve View
    if st.session_state.suggestions:
        st.divider()
        st.header("✨ CV Improvement Suggestions")
        
        # Calculate expected score
        expected_score = st.session_state.current_score
        for sug in st.session_state.suggestions:
            sug_id = sug["id"]
            if sug_id in st.session_state.accepted_suggestions:
                if not sug.get("needs_user_confirmation") or sug_id in st.session_state.confirmed_suggestions:
                    expected_score += sug.get("expected_delta", 0)
        
        # Progress bars
        col_prog1, col_prog2 = st.columns(2)
        with col_prog1:
            st.progress(st.session_state.current_score / 100, text=f"Current Score: {st.session_state.current_score}/100")
        with col_prog2:
            st.progress(expected_score / 100, text=f"Expected Score: {expected_score}/100")
        
        # Two-column layout for CV and suggestions
        col_cv, col_suggestions = st.columns([1, 1])
        
        with col_cv:
            st.subheader("📄 CV Text")
            cv_display_text = st.session_state.improved_cv_text
            
            # Highlight selected suggestion if any
            selected_sug_id = st.session_state.get("selected_suggestion_id")
            if selected_sug_id:
                for sug in st.session_state.suggestions:
                    if sug["id"] == selected_sug_id:
                        anchor_hint = sug.get("anchor_hint", "")
                        if anchor_hint:
                            start, end = locate_anchor_span(cv_display_text, anchor_hint)
                            if start < end:
                                cv_display_text = highlight_text_with_span(cv_display_text, start, end)
                                break
            
            st.markdown(f'<div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; max-height: 600px; overflow-y: auto;">{cv_display_text}</div>', unsafe_allow_html=True)
        
        with col_suggestions:
            st.subheader("💡 Suggestions")
            
            for i, sug in enumerate(st.session_state.suggestions):
                sug_id = sug["id"]
                
                # Skip ignored suggestions
                if sug_id in st.session_state.ignored_suggestions:
                    continue
                
                with st.container():
                    # Suggestion card
                    is_accepted = sug_id in st.session_state.accepted_suggestions
                    status_color = "#d4edda" if is_accepted else "#fff3cd"
                    
                    st.markdown(f'<div style="background-color: {status_color}; padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #007bff;">', unsafe_allow_html=True)
                    
                    st.write(f"**{sug['title']}** ({sug['type']}) - +{sug.get('expected_delta', 0)} pts")
                    st.caption(f"Risk: {sug.get('risk', 'low').upper()}")
                    
                    if sug.get("before"):
                        with st.expander("Before/After"):
                            st.write("**Before:**")
                            st.text(sug["before"])
                            st.write("**After:**")
                            st.text(sug["after"])
                    
                    st.write(f"**Rationale:** {sug.get('rationale', 'N/A')}")
                    
                    # Show in CV button
                    if st.button("📍 Show in CV", key=f"show_{sug_id}", use_container_width=True):
                        st.session_state.selected_suggestion_id = sug_id
                        st.rerun()
                    
                    # Confirmation checkbox if needed
                    needs_confirmation = sug.get("needs_user_confirmation", False)
                    if needs_confirmation and sug_id not in st.session_state.confirmed_suggestions:
                        confirmed = st.checkbox(
                            "I confirm this is true",
                            key=f"confirm_{sug_id}",
                            value=sug_id in st.session_state.confirmed_suggestions
                        )
                        if confirmed and sug_id not in st.session_state.confirmed_suggestions:
                            st.session_state.confirmed_suggestions.add(sug_id)
                            st.rerun()
                        if sug.get("confirmation_prompt"):
                            st.caption(f"⚠️ {sug['confirmation_prompt']}")
                    
                    # Accept/Ignore buttons
                    col_acc, col_ign = st.columns(2)
                    with col_acc:
                        if st.button("✅ Accept", key=f"accept_{sug_id}", disabled=is_accepted, use_container_width=True):
                            # Apply suggestion
                            st.session_state.improved_cv_text = apply_suggestion(
                                st.session_state.improved_cv_text,
                                sug
                            )
                            st.session_state.accepted_suggestions.add(sug_id)
                            
                            # Recompute score if needed (simplified - just increment)
                            if not needs_confirmation or sug_id in st.session_state.confirmed_suggestions:
                                st.session_state.current_score = min(100, st.session_state.current_score + sug.get("expected_delta", 0))
                            
                            st.rerun()
                    
                    with col_ign:
                        if st.button("❌ Ignore", key=f"ignore_{sug_id}", use_container_width=True):
                            st.session_state.ignored_suggestions.add(sug_id)
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.divider()


if __name__ == "__main__":
    main()
