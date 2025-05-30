"""
Transcript Processing Module

This module handles the processing of transcript PDFs and data aggregation.
It provides functionality for:
1. Processing single and multiple transcript PDFs
2. Extracting structured data using Gemini AI
3. Combining data from multiple transcripts
4. Handling duplicate detection and removal
5. Credit calculation and validation

The module ensures data consistency and handles error cases gracefully,
providing feedback through the Streamlit interface.
"""

from typing import List, Optional
import time
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .models import Student, CombinedTranscriptData
from .gemini_client import GeminiClient
from .parsers import parse_transcript_data
import pandas as pd
import json

def process_multiple_pdfs(client: GeminiClient, pdf_files: List[UploadedFile]) -> List[Student]:
    """
    Process multiple PDF transcripts in sequence.
    
    Args:
        client (GeminiClient): AI client for transcript processing
        pdf_files (List[UploadedFile]): List of uploaded transcript PDFs
        
    Returns:
        List[Student]: List of processed transcript data
        
    Each PDF is processed individually, with failures handled gracefully
    without affecting the processing of other files.
    """
    all_results = []
    
    for pdf_file in pdf_files:
        result = process_single_pdf(client, pdf_file)
        if result:
            all_results.append(result)
    
    return all_results

def process_single_pdf(client: GeminiClient, pdf_file: UploadedFile) -> Optional[Student]:
    """
    Process a single PDF transcript file.
    
    Args:
        client (GeminiClient): AI client for transcript processing
        pdf_file (UploadedFile): Uploaded transcript PDF
        
    Returns:
        Optional[Student]: Processed transcript data or None on failure
        
    Process:
    1. Read PDF content
    2. Extract data using Gemini AI
    3. Parse and validate extracted data
    4. Add source file information
    
    Provides visual feedback through Streamlit during processing.
    """
    with st.spinner(f"Currently Processing {pdf_file.name}..."):
        try:
            # Extract transcript data using AI
            pdf_content = pdf_file.read()

            # Use custom prompt if provided in session state
            prompt = st.session_state.custom_prompt or None
            result = client.process_transcript(pdf_content, prompt)
            if not result:
                st.warning(f"Failed to process {pdf_file.name}")
                return None
                
            # Parse extracted data into structured format
            parsed_data = parse_transcript_data(result)
            if not parsed_data:
                st.warning(f"Could not parse data from {pdf_file.name}")
                return None
                
            # Add source file information for tracking
            parsed_data['source_file'] = pdf_file.name
            institution_name = parsed_data.get('institution_info', {}).get('name')
            
            # Brief delay to prevent rate limiting
            time.sleep(0.5)
            return parsed_data
            
        except Exception as e:
            st.error(f"Error processing {pdf_file.name}: {str(e)}")
            return None

def combine_transcript_data(all_results: List[Student]) -> Optional[CombinedTranscriptData]:
    """
    Combine data from multiple transcripts into a single structure.
    
    Args:
        all_results (List[Student]): List of processed transcript data
        
    Returns:
        Optional[CombinedTranscriptData]: Combined data or None if no valid results
        
    Process:
    1. Initialize combined structure with first student's info
    2. Track seen institutions and courses to prevent duplicates
    3. Aggregate course data and calculate credit totals
    4. Maintain source information for each entry
    """
    if not all_results:
        return None
        
    # Initialize combined data structure
    combined_data = {
        "student_info": all_results[0].get("student_info", {}),
        "institutions": [],
        "courses": [],
        "total_credits": 0,
        "total_transfer_credits": 0
    }
    
    # Track unique entries to prevent duplicates
    seen_courses = set()
    seen_institutions = set()
    
    # Process each transcript's data
    for result in all_results:
        institution = result.get("institution_info", {})
        institution_name = institution.get("name")
        
        # Add new institutions
        if institution_name and institution_name not in seen_institutions:
            add_institution_data(
                combined_data, 
                institution, 
                institution_name, 
                seen_institutions
            )
        
        # Add courses from this institution    
        add_course_data(
            combined_data,
            result.get("courses", []),
            institution_name,
            result.get("source_file", "Unknown"),
            seen_courses
        )
    return combined_data

def add_institution_data(combined_data: dict, institution: dict, 
                        institution_name: str, 
                        seen_institutions: set):
    """
    Add institution data to combined results if not already present.
    
    Args:
        combined_data (dict): Combined transcript data
        institution (dict): Institution information
        institution_name (str): Name of institution
        seen_institutions (set): Set of processed institution names
        
    Ensures each institution is only added once to the combined data.
    """
    seen_institutions.add(institution_name)
    combined_data["institutions"].append(institution)


def add_course_data(combined_data: dict, courses: list, 
                    institution_name: str, source_file: str,
                    seen_courses: set):
    """
    Add course data to combined results, handling duplicates and credit calculation.
    
    Args:
        combined_data (dict): Combined transcript data
        courses (list): List of courses to add
        institution_name (str): Source institution name
        source_file (str): Source transcript filename
        seen_courses (set): Set of processed course keys
        
    Process:
    1. Generate unique key for each course
    2. Skip duplicates based on name, grade, and year
    3. Normalize credit values and boolean fields
    4. Calculate running credit totals
    5. Track source information
    """
    for course in courses:
        # Create unique key for duplicate detection
        course_key = f"{course.get('course_name', '')}_{course.get('grade', '')}_{course.get('year', '')}"
        
        # Process new, valid courses
        if (course_key not in seen_courses and 
            course.get('course_name')):
            # Normalize boolean fields
            course["is_transfer"] = course["is_transfer"] == "True"
            seen_courses.add(course_key)
            
            # Create standardized course entry
            course_entry = {
                "course_code": course.get("course_code", "N/A"),
                "course_name": course.get("course_name", ""),
                "credits": float(str(course.get("credits", "0")).replace(",", "").split()[0]),
                "grade": course.get("grade", ""),
                "year": course.get("year", ""),
                "is_transfer": course.get("is_transfer", False),
                "transfer_details": course.get("transfer_details",""),
                "source_institution": institution_name,
                "source_file": source_file,
                "status": course.get("status", "Unknown")
            }
            
            combined_data["courses"].append(course_entry)
            
            # Update credit totals
            try:
                credits = float(str(course.get("credits", "0")).replace(",", "").split()[0])
                combined_data["total_credits"] += credits
                if course.get("is_transfer", False):
                    combined_data["total_transfer_credits"] += credits
            except ValueError:
                st.warning(f"Could not parse credits for course: {course.get('course_code', 'Unknown')}")