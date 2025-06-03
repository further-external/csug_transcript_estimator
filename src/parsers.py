from typing import Dict, Any, Union
import json
import streamlit as st
from .models import Student

# ▸ helper stubs – keep your own implementations
def _parse_credits(val):         # str | int | float | None  →  float | None
    try:
        return float(val) if val not in (None, "") else None
    except ValueError:
        return None

def _parse_bool(val):            # "true"/"false"/bool/None  →  bool | None
    if val in (None, ""):
        return None
    if isinstance(val, bool):
        return val
    return str(val).lower() in {"true", "t", "yes", "y", "1"}


# ▸ THE FIXED FUNCTION
def parse_transcript_data(json_text: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse a transcript (JSON string *or* dict) into a normalised structure.

    Returns
    -------
    {
        "student_info": {...},
        "institution_info": {...},
        "courses": [ {...}, ... ]
    }
    """
    # 1️⃣  JSON → dict
    json_data: Dict[str, Any] = (
        json_text if isinstance(json_text, dict) else json.loads(json_text)
    )

    # 2️⃣  Initialise output
    data: Dict[str, Any] = {
        "student_info": {},
        "institution_info": {},
        "courses": [],
    }

    # 3️⃣  ---------------- Student ----------------
    # new top‑level keys
    if "first_name" in json_data or "last_name" in json_data:
        first = str(json_data.get("first_name", "")).strip()
        last  = str(json_data.get("last_name", "")).strip()
        data["student_info"]["name"] = (first + " " + last).strip()
        data["student_info"]["id"]   = str(json_data.get("student_id", ""))
    # legacy aliases
    else:
        student_raw = (
            json_data.get("Student Information")
            or json_data.get("Student")
            or json_data.get("student_info")
            or {}
        )
        data["student_info"] = {
            "name": str(student_raw.get("Name", "")),
            "id":   str(student_raw.get("ID", "")),
            "dob":  str(student_raw.get("Date of Birth", "")),
        }

    # 4️⃣  -------------- Institution --------------
    inst_raw = (
        json_data.get("institution")                               # new key
        or json_data.get("Institution Information")
        or json_data.get("Institution")
        or json_data.get("institutions")
        or json_data.get("institution_info")
        or {}
    )
    data["institution_info"] = {
        "name":     str(inst_raw.get("name", inst_raw.get("Name", ""))),
        "location": str(inst_raw.get("location", inst_raw.get("Location", ""))),
        "type":     str(inst_raw.get("institution_type", inst_raw.get("Type", ""))),
    }

    # 5️⃣  ---------------- Courses ----------------
    courses_raw = (
        json_data.get("courses")                    # new key
        or json_data.get("Course Information")
        or json_data.get("Courses")
        or []
    )

    # The sample JSON sometimes arrives as a dict with numeric keys → normalise to list
    if isinstance(courses_raw, dict):
        courses_raw = list(courses_raw.values())

    for course in courses_raw:                      # type: Dict[str, Any]
        processed = {
            # new‑style keys first, then fallbacks
            "course_code":  str(course.get("course_code",  course.get("Course Code", ""))),
            "course_name":  str(course.get("course_title", course.get("Course Name", ""))),
            "credits":      _parse_credits(course.get("credit",   course.get("Credits"))),
            "grade":        str(course.get("grade",      course.get("Grade", ""))),
            "year":         str(course.get("year",       course.get("Year", ""))),
            "is_transfer":  _parse_bool(course.get("is_transfer", course.get("Is Transfer"))),
            "transfer_details": str(course.get("transfer_details",
                                               course.get("Transfer Details", ""))),
            "status":       str(course.get("status",     course.get("Status", ""))),
        }

        # keep only real courses
        if processed["course_code"] or processed["course_name"]:
            data["courses"].append(processed)

    return data

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