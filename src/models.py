

from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Course(BaseModel):
    year: int = Field(description="The academic year in which the course was taken")
    grade: str = Field(description="The grade earned in the course")
    credit: float = Field(description="The number of credits assigned to the course")
    is_transfer: bool = Field(description="Indicates if the course was a transfer credit")
    course_code: str = Field(description="The official course code")
    course_title: str = Field(description="The title of the course")
    status: str = Field(description="The status of the course (e.g., completed, in-progress, withdrawn)")
    transfer_details: Optional[str] = Field(default=None, description="Details about the transfer if applicable")

class Institution(BaseModel):
    name: str = Field(description="The name of the institution")
    location: str = Field(description="The location (city/state/country) of the institution")
    institution_type: str = Field(description="The type of institution (e.g., University, College, High School)")

class Student(BaseModel):
    first_name: str = Field(description="The first name of the student")
    last_name: str = Field(description="The last name of the student")
    student_id: str = Field(description="A unique identifier for the student")
    institution: Institution = Field(description="The institution the student is enrolled in")
    courses: List[Course] = Field(default_factory=list, description="List of courses taken by the student")

class CombinedTranscriptData(BaseModel):
    """
    A single object that bundles everything you need to print or process
    a full transcript for one student.
    """
    student: Student = Field(..., description="Core identity and current program")
    institutions: List[Institution] = Field(..., description="All institutions represented on the transcript"
    )
    courses: List[Course] = Field(
        default_factory=list,
        description="Every course—home or transfer—appearing on the transcript",
    )
    # Totals are stored, but you can let Pydantic derive them automatically
    total_credits: float = Field(..., ge=0, description="Sum of credits for all courses")
    total_transfer_credits: float = Field(
        ..., ge=0, description="Sum of credits that came in as transfer"
    )

class TranscriptKeyData(BaseModel):
    """
    Canonical schema for transcript‑wide reference data
    (grading scales, credit definitions, etc.).
    """
    source_institution: str = Field(..., description="Name of the institution that issued the key/legend.")
    grade_scales: Dict[str, str] = Field(default_factory=dict,description="Mapping of grade symbols (e.g. 'A+') → plain‑language meanings or numeric values."
    )
    credit_definitions: List[str] = Field(
        default_factory=list,
        description="Sentences/clauses that explain how credits are awarded."
    )
    special_notations: List[str] = Field(
        default_factory=list,
        description="Text explaining symbols such as '*' or '†' that appear next to courses or grades."
    )
    transfer_indicators: List[str] = Field(
        default_factory=list,
        description="List of the symbols/phrases that mark courses accepted in transfer."
    )
    term_definitions: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of term codes (e.g. 'FA', 'SP‑7W1') → human‑readable descriptions."
    )

    class Config:
        extra = "forbid"          # reject unknown fields
        frozen = True             # instances are (hashable) read‑only