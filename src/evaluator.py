from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import re

from src.gemini_client import GeminiClient

@dataclass
class EvaluationConfig:
    current_date: datetime
    max_major_transfer_percentage: float = 50.0
    credit_age_limit_years: int = 10
    min_grade_undergraduate: str = "C-"
    min_grade_graduate: str = "B-"
    
class TransferCreditEvaluator:
    def __init__(self,client: GeminiClient, config: EvaluationConfig):
        """
        Initialize evaluator with optional PDF policy verification
        
        Args:
            config: Evaluation configuration
            policy_pdf_path: Optional path to transfer policy PDF
            gemini_api_key: Optional Gemini API key for policy verification
        """
        self.config = config
        self.client = client
        
        self._grade_values = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0
        }

    def _check_grade_requirement(self, grade: str, status: str = None) -> bool:
        """Return **True** if the course grade satisfies the minimum transfer‑
        grade threshold set by policy.

        The rules are intentionally simple and map directly to the catalog
        language supplied by Admissions:

        Transfer Grade Requirements:
        IF grade is C-/70% or higher (Undergraduate) or B- or higher (Graduate) → proceed.
        IF grade is lower → reject credit.
        IF grade is non-standard, flag for review and do not give credit 

        Args:
            grade: The raw grade value exactly as it appears on the transcript.
            status: Optional course status (e.g. 'Active').  A currently active
                    course is always in‑progress and therefore accepted.

        Returns:
            ``True`` if the grade meets the policy floor, ``False`` otherwise.
        """
        # 1. In‑progress coursework is never rejected on the basis of grade.
        if status and status.lower() == "active":
            return True

        if not grade:
            return False

        grade_clean = grade.strip().upper()

        # Helper to obtain the numeric cut‑off for the relevant program level.
        min_letter = self.config.min_grade_undergraduate
        min_value = self._grade_values.get(min_letter, 0.0)

        # 4. Letter grades – map to 4‑point scale and compare.
        course_value = self._grade_values.get(grade_clean, -1.0)
        return course_value >= min_value

    def evaluate_course(self, course: Dict) -> Dict:
        """Evaluate a single course for transfer eligibility"""
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
            'requires_manual_review': False
        }
        
        # Check for missing key fields
        missing_fields = [field for field in ['course_code', 'course_name', 'credits', 'grade', 'year']
            if not course.get(field)]

        if missing_fields:
            evaluation['requires_manual_review'] = True
            evaluation['rejection_reasons'].append('Missing data')

        # Check grade and status requirements
        grade_clean = evaluation['grade'].strip().upper()
        if grade_clean and grade_clean not in self._grade_values:
            evaluation['requires_manual_review'] = True
            evaluation['rejection_reasons'].append('Non-standard grade')
        elif grade_clean and not self._check_grade_requirement(
            course.get('grade'), 
            course.get('status')
        ):
            evaluation['rejection_reasons'].append('Grade below requirement')
            
        # Introductory course check
        course_code = course.get('course_code', '')
        match = re.search(r'\d+', course_code)
        if match:
            course_number = int(match.group(0))
            if course_number < 100:
                evaluation['rejection_reasons'].append('Introductory course')

        # Set transferable status
        evaluation['transferable'] = len(evaluation['rejection_reasons']) == 0

        return evaluation

    def evaluate_transcript(self, transcript_data: Dict, is_quarter: bool = False) -> Dict:
        """Evaluate an entire transcript"""
        # Evaluate all courses
        evaluated_courses = []
            
        for course in transcript_data.get('courses', []):
            eval_result = self.evaluate_course(course)
            
            # Adjust credit values for quarter system, if needed
            eval_result['credits_adj'] = round(eval_result['credits'] / 1.5, 2)

            evaluated_courses.append(eval_result)

        summary = {
            'total_credits': sum(course['credits'] for course in evaluated_courses),
            'total_credits_adj': sum(course['credits_adj'] for course in evaluated_courses),
            'total_transferable_credits': min(90, sum(                           # NEW – sum of credits
                course['credits'] for course in evaluated_courses
                if course['transferable']
            )),
            'total_transferable_credits_adj': min(90, sum(                           # NEW – sum of credits
                course['credits_adj'] for course in evaluated_courses
                if course['transferable']
            )),
            'total_rejected_credits': sum(
                course['credits'] for course in evaluated_courses
                if not course['transferable']
            ),
            # optional: keep a raw count too
            'transferable_courses': sum(
                1 for course in evaluated_courses if course['transferable']
            ),
            'rejected_courses': sum(
                1 for course in evaluated_courses if not course['transferable']
            ),
          
        }

        return {
            'evaluated_courses': evaluated_courses,
            'summary': summary,
        }


def create_evaluator(
    client: GeminiClient
) -> TransferCreditEvaluator:
    """Convenience factory for TransferCreditEvaluator
    
    Args:
        client: GeminiClient instance
        program_level: 'undergraduate' or 'graduate'
        max_elective_credits: Maximum number of elective credits allowed
    
    Returns:
        Configured TransferCreditEvaluator instance
    """
    config = EvaluationConfig(
        current_date=datetime.now()
    )
    
    return TransferCreditEvaluator(
        client,
        config, 
    )
