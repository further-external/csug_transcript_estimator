from datetime import datetime
from typing import Dict, List, TypedDict
from dataclasses import dataclass
from enum import Enum

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
    
class TransferCreditEvaluator:
    def __init__(self, config: EvaluationConfig):
        self.config = config
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

    def _check_grade_requirement(self, grade: str) -> bool:
        """Check if grade meets minimum requirements"""
        if not grade:
            return False
            
        # Handle Pass/Satisfactory grades
        if grade.upper() in ['P', 'S', 'CR']:
            return True  # Assuming these are equivalent to C/70% or higher as per policy
            
        min_grade = (self.config.min_grade_undergraduate 
                    if self.config.program_level == ProgramLevel.UNDERGRADUATE 
                    else self.config.min_grade_graduate)
                    
        try:
            grade_value = self._grade_values.get(grade.upper(), 0.0)
            min_grade_value = self._grade_values.get(min_grade.upper(), 0.0)
            return grade_value >= min_grade_value
        except:
            return False

    def _check_credit_age(self, course_date: datetime) -> bool:
        """Check if credits meet age requirements"""
        if not course_date:
            return True  # If no date available, assume credits are valid
            
        age_limit = self.config.credit_age_limit_years
        
        # All graduate credits must be within age limit
        if self.config.program_level == ProgramLevel.GRADUATE:
            return (self.config.current_date - course_date).days <= (age_limit * 365)
            
        return True  # Undergraduate credits don't expire by default

    def evaluate_course(self, course: Dict) -> Dict:
        """Evaluate a single course for transfer eligibility"""
        course_date = self._parse_term_date(course.get('term'), course.get('year'))
        evaluation = {
            'course_code': course.get('course_code'),
            'course_name': course.get('course_name'),
            'credits': course.get('credits', 0),
            'grade': course.get('grade'),
            'term': course.get('term'),
            'year': course.get('year'),
            'is_transfer': course.get('is_transfer', False),
            'source_institution': course.get('source_institution'),
            'transferable': False,
            'rejection_reasons': []
        }
        
        # Check grade requirements
        if not self._check_grade_requirement(course.get('grade')):
            evaluation['rejection_reasons'].append('Grade below minimum requirement')
            
        # Check credit age
        if course_date and not self._check_credit_age(course_date):
            evaluation['rejection_reasons'].append('Credits exceed age limit')
            
        # Set transferable status
        evaluation['transferable'] = len(evaluation['rejection_reasons']) == 0
        
        return evaluation

    def evaluate_transcript(self, transcript_data: Dict) -> Dict:
        """Evaluate entire transcript for transfer credit eligibility"""
        evaluation_results = {
            'student_info': transcript_data.get('student_info', {}),
            'institution_info': transcript_data.get('institutions', []),
            'evaluated_courses': [],
            'summary': {
                'total_credits_attempted': 0,
                'total_credits_accepted': 0,
                'total_courses_attempted': 0,
                'total_courses_accepted': 0,
                'rejected_courses': []
            }
        }
        
        # Evaluate each course
        for course in transcript_data.get('courses', []):
            evaluated_course = self.evaluate_course(course)
            evaluation_results['evaluated_courses'].append(evaluated_course)
            
            # Update summary statistics
            evaluation_results['summary']['total_credits_attempted'] += evaluated_course['credits']
            evaluation_results['summary']['total_courses_attempted'] += 1
            
            if evaluated_course['transferable']:
                evaluation_results['summary']['total_credits_accepted'] += evaluated_course['credits']
                evaluation_results['summary']['total_courses_accepted'] += 1
            else:
                evaluation_results['summary']['rejected_courses'].append({
                    'course_code': evaluated_course['course_code'],
                    'course_name': evaluated_course['course_name'],
                    'reasons': evaluated_course['rejection_reasons']
                })
        
        return evaluation_results

def create_evaluator(program_level: str = "undergraduate", 
                    max_elective_credits: float = 60.0) -> TransferCreditEvaluator:
    """Factory function to create a configured evaluator instance"""
    config = EvaluationConfig(
        program_level=ProgramLevel(program_level.lower()),
        current_date=datetime.now(),
        max_elective_credits=max_elective_credits
    )
    return TransferCreditEvaluator(config)