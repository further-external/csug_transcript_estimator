"""
Confidence Scoring Module

This module provides functionality to calculate confidence scores for extracted course data.
It uses multiple metrics to determine how reliable the extracted information is:
- Field completeness: Checks if all required fields are present
- Data quality: Validates data against expected patterns
- Format consistency: Ensures data follows expected formats

The confidence score is used to:
1. Identify courses that need manual review
2. Filter out low-confidence data from automatic evaluation
3. Provide transparency about data extraction reliability
"""

from typing import Dict, List, Optional
import re
from dataclasses import dataclass

@dataclass
class ConfidenceMetrics:
    """
    Container for different confidence metrics used in scoring.
    
    Attributes:
        field_completeness (float): Percentage of required fields present (0-1)
        data_quality (float): Score based on data matching expected patterns (0-1)
        format_consistency (float): Score based on data format consistency (0-1)
    """
    field_completeness: float
    data_quality: float
    format_consistency: float
    
class ConfidenceScorer:
    """
    Calculates confidence scores for extracted course data.
    
    The scorer uses multiple metrics to evaluate how reliable the extracted
    data is. Each metric contributes to the final confidence score with
    different weights.
    """
    
    def __init__(self):
        """
        Initialize the confidence scorer with validation patterns and required fields.
        
        The scorer is configured with:
        - List of required fields that should be present
        - Regex patterns for validating different data types
        - Weights for different confidence metrics
        """
        # Fields that must be present for a complete course record
        self.required_fields = [
            'course_code', 'course_name', 'credits', 
            'grade', 'term', 'year'
        ]
        
        # Regex patterns for validating data formats
        self.grade_pattern = r'^[A-F][+-]?$|^[SPI]$|^CR$|^NP$|^W$'  # Standard grade formats
        self.credit_pattern = r'^\d+\.?\d*$'  # Decimal numbers
        self.year_pattern = r'^\d{4}$'  # 4-digit years
        
    def calculate_field_completeness(self, course: Dict) -> float:
        """
        Calculate the percentage of required fields that are present and non-empty.
        
        Args:
            course (Dict): Course data dictionary
            
        Returns:
            float: Percentage of required fields present (0-1)
        """
        present_fields = sum(1 for field in self.required_fields 
                           if course.get(field))
        return present_fields / len(self.required_fields)
    
    def check_data_quality(self, course: Dict) -> float:
        """
        Validate the quality of extracted data against expected patterns.
        
        Checks:
        - Grade format matches standard patterns
        - Credits are valid numbers
        - Year is in valid format
        
        Args:
            course (Dict): Course data dictionary
            
        Returns:
            float: Quality score (0-1) based on pattern matching
        """
        quality_score = 0.0
        checks = 0
        
        # Grade format validation
        if course.get('grade'):
            checks += 1
            if re.match(self.grade_pattern, course['grade']):
                quality_score += 1
                
        # Credit format validation
        if course.get('credits'):
            checks += 1
            if isinstance(course['credits'], (int, float)) or \
               (isinstance(course['credits'], str) and 
                re.match(self.credit_pattern, course['credits'])):
                quality_score += 1
                
        # Year format validation
        if course.get('year'):
            checks += 1
            if re.match(self.year_pattern, str(course['year'])):
                quality_score += 1
                
        return quality_score / max(checks, 1)
    
    def check_format_consistency(self, course: Dict) -> float:
        """
        Check if data formats are consistent with expectations.
        
        Validates:
        - Course code minimum length
        - Course name minimum length
        
        Args:
            course (Dict): Course data dictionary
            
        Returns:
            float: Consistency score (0-1)
        """
        consistency_score = 0.0
        checks = 0
        
        # Course code length check
        if course.get('course_code'):
            checks += 1
            if len(course['course_code']) >= 3:  # Most course codes are at least 3 chars
                consistency_score += 1
        
        # Course name length check
        if course.get('course_name'):
            checks += 1
            if len(course['course_name']) >= 3:  # Course names should be descriptive
                consistency_score += 1
                
        return consistency_score / max(checks, 1)
    
    def calculate_confidence(self, course: Dict) -> float:
        """
        Calculate the overall confidence score for a course.
        
        The final score is a weighted average of:
        - Field completeness (40%)
        - Data quality (40%)
        - Format consistency (20%)
        
        Args:
            course (Dict): Course data dictionary
            
        Returns:
            float: Confidence score as a percentage (0-100)
        """
        # Calculate individual metrics
        metrics = ConfidenceMetrics(
            field_completeness=self.calculate_field_completeness(course),
            data_quality=self.check_data_quality(course),
            format_consistency=self.check_format_consistency(course)
        )
        
        # Define metric weights
        weights = {
            'field_completeness': 0.4,  # 40% weight
            'data_quality': 0.4,        # 40% weight
            'format_consistency': 0.2    # 20% weight
        }
        
        # Calculate weighted average
        confidence = (
            metrics.field_completeness * weights['field_completeness'] +
            metrics.data_quality * weights['data_quality'] +
            metrics.format_consistency * weights['format_consistency']
        )
        
        return round(confidence * 100, 1)  # Convert to percentage with 1 decimal 