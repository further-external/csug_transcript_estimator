from typing import Dict
import streamlit as st
from .models import TranscriptData

def parse_transcript_data(text: str) -> TranscriptData:
    """Parse transcript text into structured data"""
    try:
        data: TranscriptData = {
            "student_info": {},
            "institution_info": {},
            "courses": [],
            "source_file": ""
        }

        sections = text.split('\n\n')
        in_course_section = False
        current_course = {}
        course_lines = []
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            lines = section.split('\n')
            first_line = lines[0].lower().strip()
            
            if "student information" in first_line:
                for line in lines[1:]:
                    if ":" in line:
                        key, value = [x.strip() for x in line.split(":", 1)]
                        data["student_info"][key.lower()] = value
            
            elif "institution information" in first_line:
                for line in lines[1:]:
                    if ":" in line:
                        key, value = [x.strip() for x in line.split(":", 1)]
                        data["institution_info"][key.lower()] = value
            
            elif "course information" in first_line or "courses:" in first_line.lower():
                in_course_section = True
                course_lines.extend(lines[1:])
            
            elif in_course_section:
                course_lines.extend(lines)

        for line in course_lines:
            line = line.strip()
            
            if (not line) or (current_course and any(indicator in line.lower() for indicator in ["course code:", "course number:", "title:", "course name:"])):
                if current_course:
                    current_course.setdefault("course_code", "")
                    current_course.setdefault("course_name", "")
                    current_course.setdefault("credits", 0)
                    current_course.setdefault("grade", "")
                    current_course.setdefault("term", "")
                    current_course.setdefault("year", "")
                    current_course.setdefault("is_transfer", "")
                    current_course.setdefault("transfer_details", "")
                    data["courses"].append(current_course.copy())
                    current_course = {}
                
                if not line:
                    continue
            
            if ":" in line:
                key, value = [x.strip() for x in line.split(":", 1)]
                key = key.lower()
                
                key_mapping = {
                    "course code": "course_code",
                    "course number": "course_code",
                    "course name": "course_name",
                    "title": "course_name",
                    "credit": "credits",
                    "credits": "credits",
                    "grade": "grade",
                    "term": "term",
                    "year": "year",
                    "semester": "term",
                    "is_transfer": "is_transfer",
                    "transfer details": "transfer_details"
                }
                
                mapped_key = next((mapped for original, mapped in key_mapping.items() 
                                 if original in key), key)
                
                if mapped_key == "credits":
                    try:
                        credits = ''.join([c for c in value if c.isdigit() or c == '.'])
                        value = float(credits) if credits else 0
                    except ValueError:
                        value = 0
                
                current_course[mapped_key] = value

        if current_course:
            current_course.setdefault("course_code", "")
            current_course.setdefault("course_name", "")
            current_course.setdefault("credits", 0)
            current_course.setdefault("grade", "")
            current_course.setdefault("term", "")
            current_course.setdefault("year", "")
            current_course.setdefault("is_transfer", "")
            current_course.setdefault("transfer_details", "")
            data["courses"].append(current_course.copy())

        return data
        
    except Exception as e:
        st.error(f"Error parsing transcript data: {str(e)}")
        return None