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
import logging
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .models import Student, CombinedTranscriptData
from .gemini_client import GeminiClient
from .parsers import parse_transcript_data
import pandas as pd
import json

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        logger.info(f"Processing file: {pdf_file.name}")
        result = process_single_pdf(client, pdf_file)
        if result:
            all_results.append(result)
            logger.info(f"Successfully processed {pdf_file.name}")
        else:
            logger.warning(f"Failed to process {pdf_file.name}")
    
    logger.info(f"Completed processing {len(all_results)} of {len(pdf_files)} files")
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
            logger.info(f"Reading PDF content from {pdf_file.name}")
            pdf_content = pdf_file.read()

            # Use custom prompt if provided in session state
            prompt = st.session_state.custom_prompt or None
            logger.info("Sending to Gemini for extraction")
            result = client.process_transcript(pdf_content, prompt)
            
            if not result:
                logger.error(f"Gemini extraction failed for {pdf_file.name}")
                st.warning(f"Failed to process {pdf_file.name}")
                return None
                
            logger.info("Parsing extracted data")
            # Parse extracted data into structured format
            parsed_data = parse_transcript_data(result)
            if not parsed_data:
                logger.error(f"Data parsing failed for {pdf_file.name}")
                st.warning(f"Could not parse data from {pdf_file.name}")
                return None
                
            # Add source file information for tracking
            parsed_data['source_file'] = pdf_file.name
            institution_name = parsed_data.get('institution_info', {}).get('name')
            logger.info(f"Successfully processed transcript from {institution_name}")
            
            # Brief delay to prevent rate limiting
            time.sleep(0.5)
            return parsed_data
            
        except Exception as e:
            logger.exception(f"Error processing {pdf_file.name}: {str(e)}")
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
        logger.warning("No results to combine")
        return None
        
    logger.info(f"Combining data from {len(all_results)} transcripts")
        
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
            logger.info(f"Adding institution: {institution_name}")
            combined_data["institutions"].append(institution)
            seen_institutions.add(institution_name)
        
        # Add courses from this institution    
        courses = result.get("courses", [])
        logger.info(f"Processing {len(courses)} courses from {institution_name}")
        
        for course in courses:
            course_key = (
                course.get("course_code"),
                course.get("course_name"),
                institution_name
            )
            
            if course_key not in seen_courses:
                combined_data["courses"].append(course)
                seen_courses.add(course_key)
                
                # Update credit totals
                credits = course.get("credits", 0)
                combined_data["total_credits"] += credits
                if course.get("is_transfer", True):
                    combined_data["total_transfer_credits"] += credits
    
    logger.info(
        f"Combined data summary:\n"
        f"- Institutions: {len(combined_data['institutions'])}\n"
        f"- Courses: {len(combined_data['courses'])}\n"
        f"- Total Credits: {combined_data['total_credits']}\n"
        f"- Transfer Credits: {combined_data['total_transfer_credits']}"
    )
    
    return combined_data