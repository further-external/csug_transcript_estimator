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
        """
        with st.expander("Processing Details"):
            st.text(text[:200] + "...")
        """

        # Split into major sections first
        sections = text.split('\n\n')
        in_course_section = False
        current_course = {}
        
        # Collect all course lines for processing
        course_lines = []
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            lines = section.split('\n')
            first_line = lines[0].lower().strip()
            
            # Handle main sections
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
                course_lines.extend(lines[1:])  # Skip the header line
            
            elif in_course_section:
                course_lines.extend(lines)

        # Now process all course lines
        for line in course_lines:
            line = line.strip()
            
            # If we hit a blank line or course code indicator, process the current course
            if (not line) or (current_course and "course code:" in line.lower()):
                if current_course and "course_code" in current_course and "course_name" in current_course:
                    # Save complete course
                    current_course.setdefault("credits", 0)
                    current_course.setdefault("grade", "")
                    current_course.setdefault("term", "")
                    current_course.setdefault("year", "")
                    current_course["is_transfer"] = any(indicator in str(current_course).lower() 
                                                      for indicator in ["transfer", "tr ", "* ", "†"])
                    data["courses"].append(current_course.copy())
                    current_course = {}
                
                if not line:  # Skip empty lines
                    continue
            
            if ":" in line:
                key, value = [x.strip() for x in line.split(":", 1)]
                key = key.lower()
                
                # Map keys to standardized names
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
                    "semester": "term"
                }
                
                mapped_key = next((mapped for original, mapped in key_mapping.items() 
                                 if original in key), key)
                
                # Handle credits specially
                if mapped_key == "credits":
                    try:
                        credits = ''.join([c for c in value if c.isdigit() or c == '.'])
                        value = float(credits) if credits else 0
                    except ValueError:
                        value = 0
                
                current_course[mapped_key] = value

        # Process the final course if it exists
        if current_course and "course_code" in current_course and "course_name" in current_course:
            current_course.setdefault("credits", 0)
            current_course.setdefault("grade", "")
            current_course.setdefault("term", "")
            current_course.setdefault("year", "")
            current_course["is_transfer"] = any(indicator in str(current_course).lower() 
                                              for indicator in ["transfer", "tr ", "* ", "†"])
            data["courses"].append(current_course.copy())

        # Debug output
        """
        with st.expander("Parse Details"):
            st.write("Course Lines Found:", len(course_lines))
            st.write("Courses Processed:", len(data["courses"]))
            if len(data["courses"]) > 0:
                st.write("First Course:", data["courses"][0])
                st.write("Last Course:", data["courses"][-1])
        """
        
        return data
        
    except Exception as e:
        st.error(f"Error parsing transcript data: {str(e)}")
        return None