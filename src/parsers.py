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

from typing import Dict, Any, Union
import json
import streamlit as st
from .models import Student

# ▸ helper stubs – keep your own implementations
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
    try:
        return float(val) if val not in (None, "") else None
    except ValueError:
        return None

def _parse_bool(val: Any) -> bool | None:
    """
    Convert various boolean-like values to Python bool.
    
    Args:
        val: Boolean-like value (string, bool, or None)
        
    Returns:
        bool | None: Normalized boolean value or None if invalid
        
    Accepts:
    - Boolean values
    - String representations ("true", "yes", etc.)
    - Numeric strings ("1", "0")
    """
    if val in (None, ""):
        return None
    if isinstance(val, bool):
        return val
    return str(val).lower() in {"true", "t", "yes", "y", "1"}


# ▸ THE FIXED FUNCTION
def parse_transcript_data(json_text: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse and normalize transcript data from JSON.
    
    This function handles multiple input formats and produces a standardized
    dictionary structure containing student, institution, and course information.
    
    Args:
        json_text: JSON string or dictionary containing transcript data
        
    Returns:
        Dict with normalized structure:
        {
            "student_info": {
                "name": str,
                "id": str,
                "dob": str
            },
            "institution_info": {
                "name": str,
                "location": str,
                "type": str
            },
            "courses": [
                {
                    "course_code": str,
                    "course_name": str,
                    "credits": float,
                    "grade": str,
                    "year": str,
                    "is_transfer": bool,
                    "transfer_details": str,
                    "status": str
                },
                ...
            ]
        }
    """
    # Convert JSON string to dictionary if needed
    json_data: Dict[str, Any] = (
        json_text if isinstance(json_text, dict) else json.loads(json_text)
    )

    # Initialize output structure
    data: Dict[str, Any] = {
        "student_info": {},
        "institution_info": {},
        "courses": [],
    }

    # Process student information
    # Handle both new format (separate first/last name) and legacy format
    if "first_name" in json_data or "last_name" in json_data:
        # New format: separate first/last name fields
        first = str(json_data.get("first_name", "")).strip()
        last = str(json_data.get("last_name", "")).strip()
        data["student_info"]["name"] = (first + " " + last).strip()
        data["student_info"]["id"] = str(json_data.get("student_id", ""))
    else:
        # Legacy format: nested student information
        student_raw = (
            json_data.get("Student Information")
            or json_data.get("Student")
            or json_data.get("student_info")
            or {}
        )
        data["student_info"] = {
            "name": str(student_raw.get("Name", "")),
            "id": str(student_raw.get("ID", "")),
            "dob": str(student_raw.get("Date of Birth", "")),
        }

    # Process institution information
    # Handle multiple possible key names for backward compatibility
    inst_raw = (
        json_data.get("institution")                               
        or json_data.get("Institution Information")
        or json_data.get("Institution")
        or json_data.get("institutions")
        or json_data.get("institution_info")
        or {}
    )
    data["institution_info"] = {
        "name": str(inst_raw.get("name", inst_raw.get("Name", ""))),
        "location": str(inst_raw.get("location", inst_raw.get("Location", ""))),
        "type": str(inst_raw.get("institution_type", inst_raw.get("Type", ""))),
    }

    # Process course information
    # Handle multiple possible formats and key names
    courses_raw = (
        json_data.get("courses")                    
        or json_data.get("Course Information")
        or json_data.get("Courses")
        or []
    )

    # Convert dictionary of courses to list if necessary
    if isinstance(courses_raw, dict):
        courses_raw = list(courses_raw.values())

    # Process each course, normalizing field names and data types
    for course in courses_raw:
        processed = {
            # Map both new and legacy field names
            "course_code": str(course.get("course_code", course.get("Course Code", ""))),
            "course_name": str(course.get("course_title", course.get("Course Name", ""))),
            "credits": _parse_credits(course.get("credit", course.get("Credits"))),
            "grade": str(course.get("grade", course.get("Grade", ""))),
            "year": str(course.get("year", course.get("Year", ""))),
            "is_transfer": _parse_bool(course.get("is_transfer", course.get("Is Transfer"))),
            "transfer_details": str(course.get("transfer_details",
                                           course.get("Transfer Details", ""))),
            "status": str(course.get("status", course.get("Status", ""))),
        }

        # Only include courses with valid identifiers
        if processed["course_code"] or processed["course_name"]:
            data["courses"].append(processed)

    return data

def _parse_credits(credits: Any) -> float:
    """
    Parse and normalize credit values to float.
    
    Args:
        credits: Raw credit value (string, int, float, or other)
        
    Returns:
        float: Normalized credit value, 0.0 if invalid
        
    Features:
    - Strips non-numeric characters except decimal point
    - Handles various numeric formats
    - Defaults to 0.0 for invalid inputs
    - Preserves decimal precision
    """
    try:
        # Clean string inputs
        if isinstance(credits, str):
            credits = ''.join(c for c in credits if c.isdigit() or c == '.')
        
        # Convert to float with default
        return float(credits) if credits else 0.0
    except (ValueError, TypeError):
        return 0.0

def _parse_bool(value: Any) -> bool:
    """
    Parse and normalize boolean values.
    
    Args:
        value: Raw boolean-like value
        
    Returns:
        bool: Normalized boolean value
        
    Accepts:
    - Python booleans
    - String representations ('true', '1', 'yes', 'y')
    - Numeric values (converted via bool())
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'y']
    
    return bool(value)