"""
Transcript Data Parser Module

This module handles the parsing and normalization of transcript data from various formats.
It provides functionality for:
1. Converting JSON data to standardized dictionary format
2. Normalizing student information
3. Standardizing institution details
4. Processing course data with validation
5. Type conversion and data cleaning

The parser is designed to be flexible and handle multiple input formats while
producing a consistent, clean output structure suitable for evaluation.
"""

from typing import Dict, Any, Union, Optional
import json
import logging
import streamlit as st
from .models import Student, Course, Institution

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _parse_credits(val: Any) -> float | None:
    """
    Convert various credit value formats to float.
    
    Args:
        val: Credit value (string, int, float, or None)
        
    Returns:
        float | None: Normalized credit value or None if invalid
        
    Handles:
    - Numeric strings
    - Integer values
    - Float values
    - None/empty values
    """
    if val is None or val == "":
        return None
        
    try:
        # Handle string fractions
        if isinstance(val, str) and "/" in val:
            num, denom = map(float, val.split("/"))
            return num / denom
            
        # Handle normal numeric values
        return float(val)
    except (ValueError, ZeroDivisionError) as e:
        logger.warning(f"Failed to parse credit value '{val}': {str(e)}")
        return None

def _normalize_grade(grade: str) -> str:
    """Normalize grade format."""
    if not grade:
        return "N/A"
    
    grade = grade.upper().strip()
    
    # Standard letter grades
    if grade in {"A", "A-", "A+", "B+", "B", "B-", "C+", "C", "C-", 
                "D+", "D", "D-", "F"}:
        return grade
        
    # Pass/Fail variations
    if grade in {"P", "PASS", "CR", "S", "SATISFACTORY"}:
        return "P"
    if grade in {"F", "FAIL", "NC", "U", "UNSATISFACTORY"}:
        return "F"
        
    # Other standard notations
    if grade in {"W", "WD", "WITHDRAWN"}:
        return "W"
    if grade in {"I", "INC", "INCOMPLETE"}:
        return "I"
        
    logger.warning(f"Unknown grade format: {grade}")
    return grade

def parse_transcript_data(json_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse and validate transcript data from JSON string.
    
    Args:
        json_str (str): JSON string containing transcript data
        
    Returns:
        Optional[Dict[str, Any]]: Parsed and validated data or None if invalid
        
    The function:
    1. Parses JSON string
    2. Validates required fields
    3. Normalizes data formats
    4. Handles missing or invalid data
    """
    try:
        # Parse JSON string
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data: {str(e)}")
            return None
            
        # Initialize result structure
        result = {
            "student_info": {},
            "institution_info": {},
            "courses": [],
            "source_file": None
        }
        
        # Parse student information
        student_info = data.get("student_info", {})
        if not student_info.get("name"):
            logger.error("Missing required student name")
            return None
            
        result["student_info"] = {
            "name": student_info.get("name"),
            "id": student_info.get("id"),
            "program": student_info.get("program"),
            "level": student_info.get("level")
        }
        
        # Parse institution information
        inst_info = data.get("institution_info", {})
        if not inst_info.get("name"):
            logger.error("Missing required institution name")
            return None
            
        result["institution_info"] = {
            "name": inst_info.get("name"),
            "location": inst_info.get("location"),
            "accreditation": inst_info.get("accreditation")
        }
        
        # Parse course information
        courses = data.get("courses", [])
        if not courses:
            logger.warning("No courses found in transcript")
            return result
            
        for course in courses:
            try:
                # Validate required fields
                if not all(k in course for k in ["course_code", "course_name", "credits", "grade"]):
                    logger.warning(f"Skipping course with missing required fields: {course}")
                    continue
                    
                # Parse and validate credits
                credits = _parse_credits(course["credits"])
                if credits is None:
                    logger.warning(f"Skipping course with invalid credits: {course}")
                    continue
                    
                # Normalize grade
                grade = _normalize_grade(course["grade"])
                
                # Create validated course entry
                parsed_course = {
                    "course_code": course["course_code"],
                    "course_name": course["course_name"],
                    "credits": credits,
                    "grade": grade,
                    "year": course.get("year"),
                    "term": course.get("term"),
                    "is_transfer": course.get("is_transfer", True),
                    "transfer_details": course.get("transfer_details"),
                    "source_institution": inst_info.get("name"),
                    "confidence_score": 0.0,  # Will be set by confidence scorer
                    "needs_review": False
                }
                
                result["courses"].append(parsed_course)
                
            except Exception as e:
                logger.warning(f"Error parsing course: {str(e)}")
                continue
                
        # Log parsing success
        logger.info(
            f"Successfully parsed transcript with {len(result['courses'])} courses"
        )
        return result
        
    except Exception as e:
        logger.error(f"Error parsing transcript data: {str(e)}")
        return None