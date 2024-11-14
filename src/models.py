# models.py
from typing import Dict, List, TypedDict
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class InstitutionType(Enum):
    REGIONAL = "regional"
    NATIONAL = "national" 
    INTERNATIONAL = "international"
    NON_TRADITIONAL = "non_traditional"

class ProgramLevel(Enum):
    UNDERGRADUATE = "undergraduate"
    GRADUATE = "graduate"

@dataclass
class EvaluationConfig:
    program_level: ProgramLevel
    current_date: datetime
    max_elective_credits: float
    max_major_transfer_percentage: float = 50.0
    credit_age_limit_years: int = 10
    min_grade_undergraduate: str = "C-"
    min_grade_graduate: str = "B-"

class TranscriptKeyData(TypedDict):
    source_institution: str  
    grade_scales: Dict[str, str]
    credit_definitions: List[str]
    special_notations: List[str]
    transfer_indicators: List[str]
    term_definitions: Dict[str, str]

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
    transcript_key: TranscriptKeyData

class CombinedTranscriptData(TypedDict):
    student_info: Dict[str, str]
    institutions: List[Dict[str, str]]
    courses: List[CourseData]
    total_credits: float
    total_transfer_credits: float
    transcript_keys: List[TranscriptKeyData]

# Constants for grade values
GRADE_VALUES = {
    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F': 0.0
}

# Common grade options for display/input
GRADE_OPTIONS = [
    "A", "A-", "B+", "B", "B-", "C+", "C", "C-", 
    "D+", "D", "D-", "F", "P", "NP", "W", "I"
]

# Common term options
TERM_OPTIONS = ["Fall", "Winter", "Spring", "Summer"]