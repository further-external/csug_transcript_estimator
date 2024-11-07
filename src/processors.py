import time
from typing import List
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .models import TranscriptData, CombinedTranscriptData
from .gemini_client import GeminiClient
from .parsers import parse_transcript_data

def process_multiple_pdfs(client: GeminiClient, pdf_files: List[UploadedFile]) -> List[TranscriptData]:
    """Process multiple PDF transcripts"""
    all_results = []
    
    for pdf_file in pdf_files:
        with st.spinner(f"Processing {pdf_file.name}..."):
            try:
                pdf_content = pdf_file.read()
                result = client.process_transcript(pdf_content, pdf_file.name)
                if result:
                    parsed_data = parse_transcript_data(result)
                    if parsed_data:
                        parsed_data['source_file'] = pdf_file.name
                        all_results.append(parsed_data)
                    else:
                        st.warning(f"Could not parse data from {pdf_file.name}")
                else:
                    st.warning(f"Failed to process {pdf_file.name}")
                pdf_file.seek(0)
                time.sleep(0.5)
            except Exception as e:
                st.error(f"Error processing {pdf_file.name}: {str(e)}")
    
    return all_results


def combine_transcript_data(all_results: List[TranscriptData]) -> CombinedTranscriptData:
    """Combine data from multiple transcripts with corrected field mapping"""
    if not all_results:
        return None
        
    # Debug the incoming data
    with st.expander("Combine Process Details"):
        st.write(f"Number of transcripts: {len(all_results)}")
        for idx, result in enumerate(all_results):
            st.write(f"Transcript {idx + 1} courses: {len(result.get('courses', []))}")
    
    combined_data = {
        "student_info": all_results[0].get("student_info", {}),
        "institutions": [],
        "courses": [],
        "total_credits": 0,
        "total_transfer_credits": 0
    }
    
    seen_courses = set()
    

    for result in all_results:
        institution = result.get("institution_info", {})
        institution["source_file"] = result.get("source_file", "Unknown")
        if institution not in combined_data["institutions"]:
            combined_data["institutions"].append(institution)
        
        for course in result.get("courses", []):
            course_key = f"{course.get('course_code', '')}_{course.get('term', '')}_{course.get('year', '')}"
            
            if (course_key not in seen_courses and 
                course.get('course_code') and 
                course.get('course_name')):
                
                seen_courses.add(course_key)
                
                course_entry = {
                    "course_code": course.get("course_code", ""),
                    "course_name": course.get("course_name", ""),
                    "credits": float(str(course.get("credits", "0")).replace(",", "").split()[0]),
                    "grade": course.get("grade", ""),
                    "term": course.get("term", ""),
                    "year": course.get("year", ""),
                    "is_transfer": course.get("is_transfer", False),
                    "source_institution": institution.get("name", "Unknown"),
                    "source_file": result.get("source_file", "Unknown")
                }
                
                combined_data["courses"].append(course_entry)
                
                try:
                    credits = float(str(course.get("credits", "0")).replace(",", "").split()[0])
                    combined_data["total_credits"] += credits
                    if course.get("is_transfer", False):
                        combined_data["total_transfer_credits"] += credits
                except ValueError:
                    st.warning(f"Could not parse credits for course: {course.get('course_code', 'Unknown')}")
    
    # Debug the final combined data
    with st.expander("Combined Data Summary"):
        st.write(f"Total courses combined: {len(combined_data['courses'])}")
        st.write(f"Total credits: {combined_data['total_credits']}")
        
    
    return combined_data