"""
Main application module for the CSU Global Transcript Evaluator.

This module provides the Streamlit web interface for:
- Transcript upload and processing
- Credit system selection
- Evaluation results display
- Debug information
"""

import os
import logging
from pathlib import Path
import traceback
from typing import Optional
import json
import pkg_resources
import sys

import streamlit as st
import pandas as pd
from google.api_core import exceptions

from .gemini_client import (
    GeminiClient,
    GeminiError,
    APIKeyError,
    ModelError,
    ProcessingError
)
from .models import TranscriptEvaluation, Institution, Student, Course
from .config import config

# Configure logging
logger = logging.getLogger(__name__)

def check_dependencies() -> bool:
    """
    Check if all required packages are installed with correct versions.
    Returns True if all dependencies are met, False otherwise.
    """
    required = {
        "streamlit": "1.31.1",
        "google-generativeai": "0.3.2",
        "pydantic": "2.6.1",
        "tenacity": "8.0.1"  # For retry logic
    }
    
    missing = []
    outdated = []
    
    for package, version in required.items():
        try:
            installed = pkg_resources.get_distribution(package)
            if installed.version != version:
                outdated.append(f"{package} (have {installed.version}, need {version})")
        except pkg_resources.DistributionNotFound:
            missing.append(f"{package} (need {version})")
    
    if missing or outdated:
        if missing:
            st.error("📦 Missing required packages:")
            for pkg in missing:
                st.error(f"- {pkg}")
        if outdated:
            st.warning("📦 Outdated packages:")
            for pkg in outdated:
                st.warning(f"- {pkg}")
        
        st.info("Please install required packages with correct versions:")
        st.code("pip install -r requirements.txt")
        return False
        
    return True

def get_api_key() -> str:
    """Get Google API key from environment or secrets."""
    # Try environment variable first
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # Then try Streamlit secrets
    if not api_key and hasattr(st.secrets, "GOOGLE_API_KEY"):
        api_key = st.secrets.GOOGLE_API_KEY
        
    if not api_key:
        logger.error("Google API key not found")
        st.error(
            "Google API key not found. Please set GOOGLE_API_KEY in "
            "environment or .streamlit/secrets.toml"
        )
        raise APIKeyError("Missing Google API key")
        
    logger.info("Successfully loaded Google API key")
    return api_key

def display_error(error: Exception) -> None:
    """Display error message to user with appropriate context."""
    if isinstance(error, APIKeyError):
        st.error("🔑 API Key Error: Please check your API key configuration")
        if config.debug_mode:
            st.error(str(error))
    
    elif isinstance(error, ModelError):
        st.error("🤖 Model Error: Issue with the AI model configuration")
        if config.debug_mode:
            st.error(str(error))
    
    elif isinstance(error, ProcessingError):
        st.error("📄 Processing Error: Failed to process the transcript")
        if config.debug_mode:
            st.error(str(error))
    
    elif isinstance(error, exceptions.PermissionDenied):
        st.error("🔒 Permission Denied: Please check your API key permissions")
        
    elif isinstance(error, exceptions.InvalidArgument):
        st.error("⚠️ Invalid Input: Please check your input parameters")
        
    else:
        st.error("❌ An unexpected error occurred")
        if config.debug_mode:
            st.error(str(error))
            st.code(traceback.format_exc())

def display_evaluation_results(evaluation: TranscriptEvaluation):
    """Display transcript evaluation results in a structured format."""
    
    # Credit Summary
    st.header("📊 Credit Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Credits",
            f"{evaluation.total_credits:.1f}",
            help="Total credits before adjustments"
        )
    with col2:
        st.metric(
            "Transferable Credits",
            f"{evaluation.transferable_credits:.1f}",
            help="Credits eligible for transfer (max 90)"
        )
    with col3:
        st.metric(
            "Excluded Credits",
            f"{evaluation.excluded_credits:.1f}",
            help="Credits not eligible for transfer"
        )
    
    # Course Breakdown
    st.header("📚 Course Breakdown")
    
    # Convert courses to DataFrame for display
    courses_data = []
    for course in evaluation.courses:
        adjusted_credits = course.adjust_credits(
            evaluation.institution.credit_system == "quarter"
        )
        
        courses_data.append({
            "Course Code": course.course_code,
            "Course Name": course.course_name,
            "Credits": f"{adjusted_credits:.1f}",
            "Grade": course.grade,
            "Status": "Excluded" if course.is_intro_course else "Transferable",
            "Reason": get_exclusion_reason(course)
        })
    
    df = pd.DataFrame(courses_data)
    
    # Style the DataFrame
    def color_status(val):
        color = "red" if val == "Excluded" else "green"
        return f"color: {color}"
    
    styled_df = df.style.applymap(
        color_status,
        subset=["Status"]
    )
    
    # Display as a non-editable table
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Display warnings or notes
    if evaluation.transferable_credits == 90:
        st.warning("⚠️ Maximum transfer credit limit (90) reached")
    
    excluded_count = sum(1 for c in evaluation.courses if c.is_intro_course)
    if excluded_count > 0:
        st.info(f"ℹ️ {excluded_count} introductory course(s) excluded")

def get_exclusion_reason(course: Course) -> str:
    """Get the reason why a course was excluded from transfer."""
    if course.is_intro_course:
        return "Sub-100 level course"
    if course.grade not in {'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-'}:
        return "Grade not transferable"
    return "Eligible for transfer"

def process_transcript(
    client: GeminiClient,
    pdf_data: bytes,
    credit_system: str,
    show_progress: bool = True
) -> Optional[TranscriptEvaluation]:
    """
    Process transcript and create evaluation.
    
    Args:
        client: Initialized GeminiClient
        pdf_data: Raw PDF bytes
        credit_system: "semester" or "quarter"
        show_progress: Whether to show progress bar
        
    Returns:
        TranscriptEvaluation object or None on error
    """
    try:
        if show_progress:
            with st.spinner("Processing transcript..."):
                result = client.process_transcript(pdf_data)
        else:
            result = client.process_transcript(pdf_data)
            
        if result:
            # Parse the JSON response
            data = json.loads(result)
            
            # Create evaluation objects
            institution = Institution(
                **data["institution_info"],
                credit_system=credit_system
            )
            student = Student(**data["student_info"])
            courses = [Course(**course) for course in data["courses"]]
            
            # Create and calculate evaluation
            evaluation = TranscriptEvaluation(
                student=student,
                institution=institution,
                courses=courses
            )
            evaluation.calculate_credits()
            
            st.success("✅ Transcript processed successfully!")
            return evaluation
            
    except Exception as e:
        display_error(e)
        logger.exception("Failed to process transcript")
        return None

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="CSU Global Transcript Evaluator",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 CSU Global Transcript Evaluator")
    st.write(
        "Upload a transcript PDF to analyze transfer credits. "
        "The system will extract course information and evaluate transfer eligibility."
    )
    
    # Check dependencies before proceeding
    if not check_dependencies():
        return
    
    # Debug mode toggle in sidebar
    if st.sidebar.checkbox("Enable Debug Mode"):
        config.debug_mode = True
        st.sidebar.info("Debug mode enabled - detailed errors will be shown")
        
        # Show system info in debug mode
        with st.sidebar.expander("🔧 System Information"):
            st.text(f"Python version: {sys.version}")
            st.text(f"Operating system: {sys.platform}")
            st.text(f"Working directory: {os.getcwd()}")
    
    try:
        # Initialize client
        api_key = get_api_key()
        client = GeminiClient(api_key=api_key)
        
        # Credit system selection
        credit_system = st.radio(
            "Select Credit System",
            options=["semester", "quarter"],
            format_func=str.title,
            help="Choose the credit system used by the institution"
        )
        
        # File upload section
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload a transcript in PDF format"
        )
        
        if uploaded_file:
            # Process the transcript
            evaluation = process_transcript(
                client,
                uploaded_file.read(),
                credit_system
            )
            
            if evaluation:
                # Display evaluation results
                display_evaluation_results(evaluation)
                
    except Exception as e:
        display_error(e)
        logger.exception("Application error")

if __name__ == "__main__":
    main() 