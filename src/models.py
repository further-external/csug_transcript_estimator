from typing import Dict, List, TypedDict

class CourseData(TypedDict):
    course_code: str
    course_name: str
    credits: float
    grade: str
    term: str
    year: str
    is_transfer: bool
    source_institution: str
    source_file: str

class TranscriptData(TypedDict):
    student_info: Dict[str, str]
    institution_info: Dict[str, str]
    courses: List[CourseData]
    source_file: str

class CombinedTranscriptData(TypedDict):
    student_info: Dict[str, str]
    institutions: List[Dict[str, str]]
    courses: List[CourseData]
    total_credits: float
    total_transfer_credits: float