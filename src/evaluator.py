from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st

from src.gemini_client import GeminiClient

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
    transfer_policy_pdf: Optional[UploadedFile] = None
    
class TransferCreditEvaluator:
    def __init__(self,client: GeminiClient, config: EvaluationConfig, 
                 transfer_policy_pdf: UploadedFile = None):
        """
        Initialize evaluator with optional PDF policy verification
        
        Args:
            config: Evaluation configuration
            policy_pdf_path: Optional path to transfer policy PDF
            gemini_api_key: Optional Gemini API key for policy verification
        """
        self.config = config
        self.client = client
        
        if transfer_policy_pdf:
            self.transfer_policy_text = client.extract_policy_handbook(transfer_policy_pdf.read())
        

        self._grade_values = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0
        }
        
    def _parse_term_date(self, term: str, year: str) -> datetime:
        """Convert term and year to a datetime object based on standard end dates"""
        if not term or not year:
            return None
            
        try:
            year = int(year)
            term = term.lower()
            
            if term == 'Fall':
                return datetime(year, 12, 15)
            elif term == 'Spring':
                return datetime(year, 5, 15)
            elif term == 'Summer':
                return datetime(year, 8, 15)
            elif term == 'Winter':
                return datetime(year, 3, 15)
        except ValueError:
            return None
            
        return None

    def _check_grade_requirement(self, grade: str, status: str = None) -> bool:
        """
        Check if grade or status meets transfer requirements
        
        Args:
            grade: Course grade
            status: Course status (e.g., 'Active')
        
        Returns:
            Boolean indicating if the course is eligible for transfer
        """
        # Explicitly handle 'Active' status
        if status and status.lower() == 'active':
            return True
        
        if not grade:
            return False
        
        if grade.upper() in ['P', 'S', 'CR']:
            return True
        
        try:
            # Remove % symbol if present and convert to float
            grade_cleaned = grade.replace('%', '').strip()
            numeric_grade = float(grade_cleaned)
            
            # Check percentage grade
            if '%' in grade:
                return numeric_grade >= 70.0
            # Check GPA-style grade
            return numeric_grade >= 3.0
                
        except ValueError:
            min_grade = (self.config.min_grade_undergraduate 
                        if self.config.program_level == ProgramLevel.UNDERGRADUATE 
                        else self.config.min_grade_graduate)
                        
            try:
                grade_value = self._grade_values.get(grade.upper(), 0.0)
                min_grade_value = self._grade_values.get(min_grade.upper(), 0.0)
                return grade_value >= min_grade_value
            except:
                return False
            
    def evaluate_course(self, course: Dict) -> Dict:
        """Evaluate a single course for transfer eligibility"""
        course_date = self._parse_term_date(course.get('term'), course.get('year'))
        evaluation = {
            'course_code': course.get('course_code'),
            'course_name': course.get('course_name'),
            'credits': course.get('credits', 0),
            'grade': course.get('grade'),
            'status': course.get('status'),
            'term': course.get('term'),
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
            
        # Check credit age
        if course_date and not self._check_credit_age(course_date):
            evaluation['rejection_reasons'].append('Credits exceed age limit')
            
        # Set transferable status
        evaluation['transferable'] = len(evaluation['rejection_reasons']) == 0
        
        # Additional policy verification if policy verifier is set up
        if self.transfer_policy_text:
            try:
                transfer_policy_verification = self.client.verify_with_policy_handbook(
                    course, 
                    self.transfer_policy_text
                )
                st.warning(transfer_policy_verification)
                
                # Merge policy verification results
                if transfer_policy_verification:
                    evaluation['transfer_policy_verification'] = transfer_policy_verification
                    
                    # Override transferability if policy verification provides definitive input
                    if transfer_policy_verification.get('transfer_policy_verified'):
                        evaluation['transferable'] = transfer_policy_verification.get('is_transferable', evaluation['transferable'])
                        
                        # Add policy-related rejection reasons if applicable
                        if not transfer_policy_verification.get('is_transferable'):
                            evaluation['rejection_reasons'].append('Failed policy verification')
            
            except Exception as e:
                #print(f"Error in evaluate course: {e}")
                evaluation['transfer_policy_verification_error'] = str(e)
        
        return evaluation
        
    
    def evaluate_transcript(self, transcript_data: Dict) -> Dict:
        """
        Evaluate entire transcript for transfer credit eligibility with policy verification
        
        Args:
            transcript_data: Transcript information dictionary
        
        Returns:
            Comprehensive evaluation results including policy verification
        """
        evaluation_results = {
            'student_info': transcript_data.get('student_info', {}),
            'institution_info': transcript_data.get('institution_info', {}),
            'evaluated_courses': [],
            'summary': {
                'total_credits_attempted': 0,
                'total_credits_accepted': 0,
                'total_courses_attempted': 0,
                'total_courses_accepted': 0,
                'rejected_courses': [],
                'policy_verification_summary': {
                    'total_verified_courses': 0,
                    'total_policy_exceptions': 0,
                    'verified_courses_details': []
                }
            }
        }
        
        # Evaluate each course
        for course in transcript_data.get('courses', []):
            # Perform course evaluation
            evaluated_course = self.evaluate_course(course)
            evaluation_results['evaluated_courses'].append(evaluated_course)
            
            # Update summary statistics for course attempts
            evaluation_results['summary']['total_credits_attempted'] += evaluated_course.get('credits', 0)
            evaluation_results['summary']['total_courses_attempted'] += 1
            
            # Track policy verification details
            if evaluated_course.get('transfer_policy_verification'):
                policy_ver = evaluated_course['transfer_policy_verification']
                policy_summary = evaluation_results['summary']['policy_verification_summary']
                
                policy_summary['total_verified_courses'] += 1
                
                # Track policy exceptions or interesting cases
                if not policy_ver.get('is_transferable', False):
                    policy_summary['total_policy_exceptions'] += 1
                
                # Store detailed policy verification for reference
                policy_summary['verified_courses_details'].append({
                    'course_code': evaluated_course.get('course_code'),
                    'course_name': evaluated_course.get('course_name'),
                    'is_transferable': policy_ver.get('is_transferable', False),
                    'confidence_score': policy_ver.get('confidence_score', 0),
                    'supporting_clauses': policy_ver.get('supporting_clauses', []),
                    'additional_notes': policy_ver.get('additional_notes', '')
                })
            
            # Update accepted courses
            if evaluated_course.get('transferable'):
                evaluation_results['summary']['total_credits_accepted'] += evaluated_course.get('credits', 0)
                evaluation_results['summary']['total_courses_accepted'] += 1
            else:
                # Track rejected courses
                evaluation_results['summary']['rejected_courses'].append({
                    'course_code': evaluated_course.get('course_code'),
                    'course_name': evaluated_course.get('course_name'),
                    'reasons': evaluated_course.get('rejection_reasons', [])
                })
        
        return evaluation_results

def create_evaluator(
    client: GeminiClient,
    transfer_policy_pdf: UploadedFile,
    program_level: str = "undergraduate", 
    max_elective_credits: float = 60.0) -> TransferCreditEvaluator:
    """
    Factory function to create a configured evaluator instance with optional policy verification
    
    Args:
        program_level: Program level for evaluation
        max_elective_credits: Maximum elective credits
        policy_pdf_path: Optional path to transfer policy PDF
        gemini_api_key: Optional Gemini API key
    
    Returns:
        Configured TransferCreditEvaluator instance
    """
    config = EvaluationConfig(
        program_level=ProgramLevel(program_level.lower()),
        current_date=datetime.now(),
        max_elective_credits=max_elective_credits,
        transfer_policy_pdf= transfer_policy_pdf,
    )
    
    return TransferCreditEvaluator(
        client,
        config, 
        transfer_policy_pdf=transfer_policy_pdf, 
    )