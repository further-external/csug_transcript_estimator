# processors.py
from typing import List, Optional
import time
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .models import Student,CombinedTranscriptData
from .gemini_client import GeminiClient
from .parsers import parse_transcript_data
import pandas as pd
import json

def process_multiple_pdfs(client: GeminiClient, pdf_files: List[UploadedFile]) -> List[Student]:
    """Process multiple PDF transcripts"""
    all_results = []
    
    for pdf_file in pdf_files:
        result = process_single_pdf(client, pdf_file)
        if result:
            all_results.append(result)
    
    return all_results

def process_single_pdf(client: GeminiClient, pdf_file: UploadedFile) -> Optional[Student]:
    """Process a single PDF transcript"""
    with st.spinner(f"Currently Processing {pdf_file.name}..."):
        try:
            # Extract main transcript data
            pdf_content = pdf_file.read()
            result = client.process_transcript(pdf_content, pdf_file.name)
            if not result:
                st.warning(f"Failed to process {pdf_file.name}")
                return None
            parsed_data = parse_transcript_data(result)
            if not parsed_data:
                st.warning(f"Could not parse data from {pdf_file.name}")
                return None
                
            parsed_data['source_file'] = pdf_file.name
            #st.write(parsed_data)
            institution_name = parsed_data.get('institution_info', {}).get('name')
            
            if institution_name:
                # Extract transcript key
                pdf_file.seek(0)
                key_data = client.extract_transcript_key(
                    pdf_content=pdf_file.read(),
                    institution_name=institution_name
                )
                
                if key_data:
                    parsed_data['transcript_key'] = key_data
            
            time.sleep(0.5)
            return parsed_data
            
        except Exception as e:
            st.error(f"Error processing {pdf_file.name}: {str(e)}")
            return None

def combine_transcript_data(all_results: List[Student]) -> Optional[CombinedTranscriptData]:
    """Combine data from multiple transcripts"""
    if not all_results:
        return None
        
    combined_data = {
        "student_info": all_results[0].get("student_info", {}),
        "institutions": [],
        "courses": [],
        "transcript_keys": [],
        "total_credits": 0,
        "total_transfer_credits": 0
    }
    
    seen_courses = set()
    seen_institutions = set()
    
    for result in all_results:
        institution = result.get("institution_info", {})
        institution_name = institution.get("name")
        
        if institution_name and institution_name not in seen_institutions:
            add_institution_data(
                combined_data, 
                institution, 
                institution_name, 
                result.get("transcript_key"),
                seen_institutions
            )
            
        add_course_data(
            combined_data,
            result.get("courses", []),
            institution_name,
            result.get("source_file", "Unknown"),
            seen_courses
        )
        #print(combined_data)
    return combined_data

def add_institution_data(combined_data: dict, institution: dict, 
                        institution_name: str, transcript_key: dict, 
                        seen_institutions: set):
    """Add institution and transcript key data to combined results"""
    seen_institutions.add(institution_name)
    combined_data["institutions"].append(institution)
    
    if transcript_key:
        if institution_name != transcript_key.get("source_institution"):
            transcript_key["source_institution"] = institution_name
        combined_data["transcript_keys"].append(transcript_key)

def add_course_data(combined_data: dict, courses: list, 
                    institution_name: str, source_file: str,
                    seen_courses: set):
    """Add course data to combined results"""
    for course in courses:
        course_key = f"{course.get('course_name', '')}_{course.get('grade', '')}_{course.get('year', '')}"
        
        if (course_key not in seen_courses and 
            course.get('course_name')):
            course["is_transfer"] = course["is_transfer"] == "True"
            seen_courses.add(course_key)
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
            
            try:
                credits = float(str(course.get("credits", "0")).replace(",", "").split()[0])
                combined_data["total_credits"] += credits
                if course.get("is_transfer", False):
                    combined_data["total_transfer_credits"] += credits
            except ValueError:
                st.warning(f"Could not parse credits for course: {course.get('course_code', 'Unknown')}")