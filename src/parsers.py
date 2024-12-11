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

        for i, line in enumerate(course_lines):
            line = line.strip()
            
            # Handle course code and name when they appear on separate lines
            if line and not ":" in line and not current_course:
                current_course = {"course_code": line}
                # Check next line for course name if available
                if i + 1 < len(course_lines):
                    next_line = course_lines[i + 1].strip()
                    if not ":" in next_line:
                        current_course["course_name"] = next_line
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
                
                # Start new course entry if we hit another course code/name
                if mapped_key in ["course_code", "course_name"] and current_course.get(mapped_key):
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
                
                current_course[mapped_key] = value

                # If we've collected all course details, save the course
                if all(k in current_course for k in ["course_code", "course_name", "credits", "grade"]):
                    current_course.setdefault("term", "")
                    current_course.setdefault("year", "")
                    current_course.setdefault("is_transfer", "")
                    current_course.setdefault("transfer_details", "")
                    data["courses"].append(current_course.copy())
                    current_course = {}

        # Add any remaining course
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

        # Clean up any duplicate or incomplete entries
        cleaned_courses = []
        seen_courses = set()
        for course in data["courses"]:
            course_key = f"{course['course_code']}_{course['course_name']}"
            if course_key not in seen_courses:
                seen_courses.add(course_key)
                if course["course_code"] or course["course_name"]:
                    cleaned_courses.append(course)
        
        data["courses"] = cleaned_courses

        return data
        
    except Exception as e:
        st.error(f"Error parsing transcript data: {str(e)}")
        return None