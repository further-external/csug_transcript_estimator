"""
Transfer Credit Evaluation Module

This module handles the evaluation of transfer credits according to CSU Global's policies.
It implements:
1. Grade requirement checking
2. Confidence score integration
3. Credit transfer eligibility determination
4. Summary statistics calculation

The evaluation process follows these steps:
1. Calculate confidence score for each course
2. Filter out low-confidence courses for manual review
3. Apply grade requirements to high-confidence courses
4. Generate detailed evaluation results and summary statistics
"""

from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import re

from src.gemini_client import GeminiClient
from src.confidence_scorer import ConfidenceScorer

@dataclass
class EvaluationConfig:
    """
    Configuration settings for transfer credit evaluation.
    
    Attributes:
        current_date (datetime): Current date for age-based calculations
        max_major_transfer_percentage (float): Maximum percentage of major credits that can transfer
        credit_age_limit_years (int): Maximum age of credits to be considered
        min_grade_undergraduate (str): Minimum acceptable grade for undergraduate transfer
        min_grade_graduate (str): Minimum acceptable grade for graduate transfer
        min_confidence_threshold (float): Minimum confidence score to evaluate automatically
    """
    current_date: datetime
    max_major_transfer_percentage: float = 50.0
    credit_age_limit_years: int = 10
    min_grade_undergraduate: str = "C-"
    min_grade_graduate: str = "B-"
    min_confidence_threshold: float = 80.0
    
class TransferCreditEvaluator:
    """
    Evaluates transfer credits according to institutional policies.
    
    This class handles:
    - Confidence score calculation
    - Grade requirement verification
    - Transfer eligibility determination
    - Summary statistics generation
    """
    
    def __init__(self, client: GeminiClient, config: EvaluationConfig):
        """
        Initialize the evaluator with configuration and scoring tools.
        
        Args:
            client (GeminiClient): Client for AI-assisted evaluation
            config (EvaluationConfig): Evaluation configuration settings
        """
        self.config = config
        self.client = client
        self.confidence_scorer = ConfidenceScorer()
        
        # Grade point values for GPA calculation and comparison
        self._grade_values = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0
        }

    def _check_grade_requirement(self, grade: str, status: str = None) -> bool:
        """
        Check if a course's grade meets transfer requirements.
        
        Rules:
        1. Active courses are always accepted (in-progress)
        2. Pass/Satisfactory grades need transcript key verification
        3. Letter grades must meet minimum GPA requirement
        
        Args:
            grade (str): The course grade
            status (str, optional): Course status (e.g., 'Active')
            
        Returns:
            bool: True if grade meets requirements, False otherwise
        """
        if status and status.lower() == "active":
            return True

        if not grade:
            return False

        grade_clean = grade.strip().upper()

        # Pass/Satisfactory grades need manual verification
        if grade_clean in {"P", "S", "CR"}:
            return True

        # Convert letter grades to numeric values and compare
        min_letter = self.config.min_grade_undergraduate
        min_value = self._grade_values.get(min_letter, 0.0)
        course_value = self._grade_values.get(grade_clean, -1.0)
        
        return course_value >= min_value

    def evaluate_course(self, course: Dict) -> Dict:
        """
        Evaluate a single course for transfer eligibility.
        
        Process:
        1. Calculate confidence score
        2. If confidence is low, mark for review
        3. If confidence is high, check grade requirements
        4. Determine final transfer status
        
        Args:
            course (Dict): Course data to evaluate
            
        Returns:
            Dict: Evaluation results including:
                - Confidence score
                - Transfer status
                - Rejection reasons (if any)
                - Review status
        """
        # Initialize evaluation result
        evaluation = {
            'course_code': course.get('course_code'),
            'course_name': course.get('course_name'),
            'credits': course.get('credits', 0),
            'grade': course.get('grade'),
            'status': course.get('status'),
            'year': course.get('year'),
            'is_transfer': course.get('is_transfer', False),
            'source_institution': course.get('source_institution'),
            'transferable': False,
            'rejection_reasons': [],
            'confidence_score': 0.0,
            'needs_review': False
        }
        
        # Calculate and check confidence score
        evaluation['confidence_score'] = self.confidence_scorer.calculate_confidence(course)
        
        if evaluation['confidence_score'] < self.config.min_confidence_threshold:
            evaluation['needs_review'] = True
            evaluation['rejection_reasons'].append(
                f'Low confidence score ({evaluation["confidence_score"]}%)'
            )
            return evaluation
        
        # Check grade requirements for high-confidence courses
        if not self._check_grade_requirement(
            course.get('grade'), 
            course.get('status')
        ):
            evaluation['rejection_reasons'].append('Grade or status below requirement')
            
        # Introductory course check
        course_code = course.get('course_code', '')
        match = re.search(r'\d+', course_code)
        if match:
            course_number = int(match.group(0))
            if course_number < 100:
                evaluation['rejection_reasons'].append('Introductory course (course number below 100)')

        # Set final transfer status
        evaluation['transferable'] = len(evaluation['rejection_reasons']) == 0
        return evaluation

    def evaluate_transcript(self, transcript_data: Dict, is_quarter: bool = False) -> Dict:
        """
        Evaluate an entire transcript and generate summary statistics.
        
        Process:
        1. Evaluate each course
        2. Separate high and low confidence courses
        3. Calculate credit totals and counts
        4. Generate summary statistics
        
        Args:
            transcript_data (Dict): Complete transcript data
            
        Returns:
            Dict: Evaluation results including:
                - List of evaluated courses
                - Summary statistics
                - Credit totals by category
        """
        # Evaluate all courses
        evaluated_courses = []
            
        for course in transcript_data.get('courses', []):
            eval_result = self.evaluate_course(course)
            
            # Adjust credit values for quarter system
            if is_quarter:
                eval_result['credits'] = round(eval_result['credits'] / 1.5, 2)
            
            evaluated_courses.append(eval_result)

        # Separate courses by confidence level
        high_confidence_courses = [
            course for course in evaluated_courses 
            if course['confidence_score'] >= self.config.min_confidence_threshold
        ]
        low_confidence_courses = [
            course for course in evaluated_courses 
            if course['confidence_score'] < self.config.min_confidence_threshold
        ]

        # Calculate summary statistics
        summary = {
            'total_credits': sum(course['credits'] for course in evaluated_courses),
            'total_transferable_credits': min(90, sum(
                course['credits'] for course in high_confidence_courses
                if course['transferable'])
            ),
            'total_rejected_credits': sum(
                course['credits'] for course in high_confidence_courses
                if not course['transferable']
            ),
            'low_confidence_credits': sum(
                course['credits'] for course in low_confidence_courses
            ),
            'transferable_courses': sum(
                1 for course in high_confidence_courses if course['transferable']
            ),
            'rejected_courses': sum(
                1 for course in high_confidence_courses if not course['transferable']
            ),
            'low_confidence_courses': len(low_confidence_courses)
        }

        return {
            'evaluated_courses': evaluated_courses,
            'summary': summary,
        }


def create_evaluator(client: GeminiClient) -> TransferCreditEvaluator:
    """
    Factory function to create a configured TransferCreditEvaluator.
    
    Args:
        client (GeminiClient): Client for AI-assisted evaluation
        
    Returns:
        TransferCreditEvaluator: Configured evaluator instance
    """
    config = EvaluationConfig(
        current_date=datetime.now()
    )
    
    return TransferCreditEvaluator(
        client,
        config
    )
