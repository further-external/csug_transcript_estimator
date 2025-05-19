from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st

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

        * **Undergraduate programs** → C‑ / 70 % or better  
        * **Graduate programs**      → B‑ or better  
        * Grades below the threshold → **Reject**  
        * Institutional grades of **S**, **P** or **CR** may be accepted *when*
          the transcript key confirms they represent at least a C/70 % or higher
          at the sending institution.  Because we do not (yet) parse the
          transcript key, these grades are provisionally treated as acceptable
          and flagged for manual verification upstream.

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

        # 2. Straight‑through accept for institutional pass indicators that must
        #    still be confirmed by a human reader against the transcript key.
        if grade_clean in {"P", "S", "CR"}:
            return True

        # Helper to obtain the numeric cut‑off for the relevant program level.
        min_letter = self.config.min_grade_undergraduate
        min_value = self._grade_values.get(min_letter, 0.0)

        # 3. Handle explicit percentages – e.g. "85%" or "79".
        try:
            # Remove a trailing % if present.
            percent = float(grade_clean.replace('%', ''))
            # Treat values up to 4.0 as GPA; otherwise percentage.
            if percent <= 4.0:
                # GPA scale (0‑4).  Compare to the minimum letter value.
                return percent >= min_value
            else:
                return percent >= 70.0  # Policy floor for both UG & GR percentages.
        except ValueError:
            # Not a pure numeric grade – fall through to letter evaluation.
            pass

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
            'rejection_reasons': []
        }
        
        # Check grade and status requirements
        if not self._check_grade_requirement(
            course.get('grade'), 
            course.get('status')
        ):
            evaluation['rejection_reasons'].append('Grade or status below requirement')
            
        # Set transferable status
        evaluation['transferable'] = len(evaluation['rejection_reasons']) == 0

        return evaluation

    def evaluate_transcript(self, transcript_data: Dict) -> Dict:
        """Evaluate an entire transcript"""
        evaluated_courses = [self.evaluate_course(course) for course in transcript_data.get('courses', [])]

        summary = {
            'total_courses': len(evaluated_courses),
            'transferable_courses': sum(course['transferable'] for course in evaluated_courses),
            'rejected_courses': sum(not course['transferable'] for course in evaluated_courses),
            'rejection_reasons_summary': {},
        }

        # Aggregate rejection reasons
        for course in evaluated_courses:
            for reason in course['rejection_reasons']:
                summary['rejection_reasons_summary'][reason] = summary['rejection_reasons_summary'].get(reason, 0) + 1

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
