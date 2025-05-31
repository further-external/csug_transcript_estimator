"""
Data Models Module

This module defines the core data models used throughout the transcript evaluation system.
It provides Pydantic models for:
1. Student information
2. Institution details
3. Course data with confidence scoring
4. Combined transcript data with evaluation metrics

The models enforce data validation and provide a consistent structure for:
- Data extraction from transcripts
- Transfer credit evaluation
- Results presentation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
import re

class Course(BaseModel):
    """
    Course information model with confidence scoring and validation.
    
    This model represents a single course from a transcript, including:
    - Basic course information (code, name, credits)
    - Grade and academic period
    - Transfer status and details
    - Confidence metrics for data extraction
    - Review status flags
    
    The model is used both for data extraction and evaluation results.
    """
    course_code: str = Field(
        ..., 
        description="Course code/number as it appears on transcript"
    )
    course_name: str = Field(
        ..., 
        description="Full course name/title"
    )
    credits: float = Field(
        ..., 
        ge=0, 
        description="Number of credit hours"
    )
    grade: str = Field(
        ..., 
        description="Course grade (A-F, P/F, etc.)"
    )
    year: Optional[str] = Field(
        None, 
        description="Academic year course was taken"
    )
    term: Optional[str] = Field(
        None, 
        description="Academic term (Fall, Spring, etc.)"
    )
    is_transfer: bool = Field(
        default=False, 
        description="Indicates if course is from another institution"
    )
    is_intro_course: bool = Field(
        default=False,
        description="Indicates if course is introductory (sub-100 level)"
    )
    transfer_details: Optional[str] = Field(
        None, 
        description="Additional transfer credit information"
    )
    source_institution: Optional[str] = Field(
        None, 
        description="Institution where course was taken"
    )
    source_file: Optional[str] = Field(
        None, 
        description="Name of transcript file"
    )
    credit_category: Optional[str] = Field(
        None, 
        description="Category for credit application (Gen Ed, Major, etc.)"
    )
    confidence_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=100.0, 
        description="Confidence score for extracted data (0-100)"
    )
    needs_review: bool = Field(
        default=False,
        description="Flag indicating manual review needed"
    )
    status: Optional[str] = Field(
        None, 
        description="Course status (Complete, In Progress, etc.)"
    )
    notes: Optional[str] = Field(
        None, 
        description="Additional notes or comments"
    )

    @validator("course_code")
    def validate_course_code(cls, v):
        """Validate course code and set is_intro_course flag."""
        # Extract numeric part of course code
        numbers = re.findall(r'\d+', v)
        if numbers:
            course_number = int(numbers[0])
            # Set is_intro_course for sub-100 level courses
            cls.is_intro_course = course_number < 100
        return v
    
    @validator("grade")
    def validate_grade(cls, v):
        """Validate if grade is considered passing."""
        # Normalize grade to uppercase
        v = v.upper()
        # Define passing grades (excluding S and P)
        passing_grades = {'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-'}
        if v not in passing_grades:
            raise ValueError(f"Grade {v} is not considered passing")
        return v
    
    def adjust_credits(self, is_quarter_system: bool) -> float:
        """
        Adjust credits based on quarter/semester system.
        Quarter credits are converted to semester credits (2/3 ratio).
        """
        if is_quarter_system:
            return round(self.credits * (2/3), 2)
        return self.credits

class Institution(BaseModel):
    """
    Institution information model.
    
    Represents an academic institution with:
    - Basic identification (name, location)
    - Classification details
    - Accreditation status
    
    Used for both source and destination institutions.
    """
    name: str = Field(
        ..., 
        description="Official institution name"
    )
    location: Optional[str] = Field(
        None, 
        description="Geographic location"
    )
    type: Optional[str] = Field(
        None, 
        description="Institution type (University, College, etc.)"
    )
    accreditation: Optional[str] = Field(
        None, 
        description="Current accreditation status"
    )
    credit_system: str = Field(
        default="semester",
        description="Credit system used (semester or quarter)"
    )

    @validator("credit_system")
    def validate_credit_system(cls, v):
        """Validate credit system type."""
        valid_systems = {"semester", "quarter"}
        v = v.lower()
        if v not in valid_systems:
            raise ValueError(f"Credit system must be one of: {', '.join(valid_systems)}")
        return v

class Student(BaseModel):
    """
    Student information model.
    
    Contains core student identification data:
    - Name
    - Student ID
    - Date of birth
    
    Used for transcript matching and record keeping.
    """
    name: str = Field(
        ..., 
        description="Student's full legal name"
    )
    id: Optional[str] = Field(
        None, 
        description="Institution-assigned student ID"
    )
    dob: Optional[str] = Field(
        None, 
        description="Student's date of birth"
    )
    program: Optional[str] = Field(
        None,
        description="Student's program or major"
    )

class CombinedTranscriptData(BaseModel):
    """
    Combined transcript data model with evaluation metrics.
    
    This model aggregates all transcript-related data:
    - Student information
    - Institution details
    - Course listings
    - Credit totals
    - Confidence metrics
    
    Used as the main data structure for evaluation and reporting.
    """
    student: Student = Field(
        ..., 
        description="Student's personal information"
    )
    institutions: List[Institution] = Field(
        ..., 
        description="All institutions on transcript"
    )
    courses: List[Course] = Field(
        default_factory=list,
        description="All courses from transcript"
    )
    total_credits: float = Field(
        ..., 
        ge=0, 
        description="Total credits attempted"
    )
    total_transfer_credits: float = Field(
        ..., 
        ge=0, 
        description="Total credits eligible for transfer"
    )
    total_low_confidence_credits: float = Field(
        default=0.0,
        ge=0,
        description="Total credits needing manual review"
    )
    average_confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Average confidence across all courses"
    )

class TranscriptEvaluation(BaseModel):
    """
    Transcript evaluation results with credit calculations and limits.
    
    This model enforces:
    - Maximum 90 transferable credits
    - Exclusion of sub-100 level courses
    - Quarter to semester credit conversion
    - Grade requirements (no S/P grades)
    """
    
    student: Student
    institution: Institution
    courses: List[Course]
    
    # Credit calculation fields
    total_credits: float = Field(
        default=0.0,
        description="Total credits before adjustments"
    )
    transferable_credits: float = Field(
        default=0.0,
        description="Credits eligible for transfer"
    )
    excluded_credits: float = Field(
        default=0.0,
        description="Credits excluded from transfer"
    )
    
    # Metadata
    evaluation_date: datetime = Field(
        default_factory=datetime.now,
        description="When the evaluation was performed"
    )
    
    def calculate_credits(self):
        """
        Calculate credit totals with all rules applied:
        - Convert quarter credits if needed
        - Exclude sub-100 level courses
        - Apply 90 credit maximum
        - Only count passing grades
        """
        is_quarter = self.institution.credit_system == "quarter"
        total = 0.0
        transferable = 0.0
        excluded = 0.0
        
        for course in self.courses:
            # Adjust credits for quarter system
            adjusted_credits = course.adjust_credits(is_quarter)
            total += adjusted_credits
            
            # Check if course is transferable
            if (not course.is_intro_course and 
                course.grade in {'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-'}):
                transferable += adjusted_credits
            else:
                excluded += adjusted_credits
        
        # Cap transferable credits at 90
        if transferable > 90:
            excluded += (transferable - 90)
            transferable = 90
            
        self.total_credits = round(total, 2)
        self.transferable_credits = round(transferable, 2)
        self.excluded_credits = round(excluded, 2)
        
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True  # Validate when attributes are set
        extra = "forbid"  # Prevent additional attributes
        frozen = True  # Make the model immutable after creation
