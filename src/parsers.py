from typing import Dict, Any
import json
import streamlit as st
from .models import TranscriptData

def parse_transcript_data(json_text: str) -> TranscriptData:
    """Parse transcript JSON into structured data"""
    try:
        # Parse the JSON string into a Python dictionary
        json_data = json.loads(json_text)
        st.json(json_text)
        
        # Initialize the TranscriptData structure
        data: TranscriptData = {
            "student_info": {},
            "institution_info": {},
            "courses": [],
            "source_file": ""
        }
        
        # Parse student information
        student_info = json_data.get("Student Information", {})
        data["student_info"] = {
            "name": str(student_info.get("Name", "")),
            "id": str(student_info.get("ID", "")),
            "program": str(student_info.get("Program", ""))
        }
        
        # Parse institution information
        institution_info = json_data.get("Institution Information", {})
        data["institution_info"] = {
            "name": str(institution_info.get("Name", "")),
            "location": str(institution_info.get("Location", ""))
        }
        
        # Parse courses
        courses = json_data.get("Course Information", [])
        for course in courses:
            processed_course = {
                "course_code": str(course.get("Course Code", "")),
                "course_name": str(course.get("Course Name", "")),
                "credits": _parse_credits(course.get("Credits")),
                "grade": str(course.get("Grade", "")),
                "term": str(course.get("Term", "")),
                "year": str(course.get("Year", "")),
                "is_transfer": _parse_bool(course.get("Is Transfer")),
                "transfer_details": str(course.get("Transfer Details", "")),
                "status": str(course.get("Status", ""))
            }
            
            # Only add course if it has a course code or name
            if processed_course["course_code"] or processed_course["course_name"]:
                data["courses"].append(processed_course)
        
        return data
    
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error parsing transcript data: {str(e)}")
        return None

def _parse_credits(credits: Any) -> float:
    """
    Parse credits to ensure it's a float value
    
    Args:
        credits: Input credits value
    
    Returns:
        Float representation of credits, defaults to 0 if conversion fails
    """
    try:
        # Handle string, int, or float inputs
        if isinstance(credits, str):
            # Remove any non-numeric characters except decimal point
            credits = ''.join(c for c in credits if c.isdigit() or c == '.')
        
        # Convert to float, default to 0 if empty or conversion fails
        return float(credits) if credits else 0.0
    except (ValueError, TypeError):
        return 0.0

def _parse_bool(value: Any) -> bool:
    """
    Parse boolean value safely
    
    Args:
        value: Input value to convert to boolean
    
    Returns:
        Boolean representation of the input
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'y']
    
    return bool(value)