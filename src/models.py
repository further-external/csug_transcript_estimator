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

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class Course(BaseModel):
    """
    Course information model with confidence scoring.
    
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
