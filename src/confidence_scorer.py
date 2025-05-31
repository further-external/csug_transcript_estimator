"""
Confidence Scoring Module

This module calculates confidence scores for transcript evaluation results.
It considers:
1. Data completeness
2. Grade validity
3. Course level appropriateness
4. Credit system consistency
5. Overall evaluation reliability

The scoring system helps identify entries that may need manual review.
"""

import re
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime

from .models import Course, Institution, TranscriptEvaluation

# Configure logging
logger = logging.getLogger(__name__)

class ConfidenceScorer:
    """
    Calculates confidence scores for transcript evaluation results.
    
    Features:
    - Course-level scoring
    - Grade validation
    - Credit system checks
    - Data completeness assessment
    - Manual review flagging
    """
    
    # Valid grade patterns and weights
    VALID_GRADES: Set[str] = {
        'A+', 'A', 'A-',
        'B+', 'B', 'B-',
        'C+', 'C', 'C-'
    }
    
    # Confidence weights for different factors
    WEIGHTS = {
        'course_code': 0.25,    # Weight for course code validation
        'grade': 0.25,          # Weight for grade validation
        'credits': 0.20,        # Weight for credit value validation
        'completeness': 0.15,   # Weight for data completeness
        'consistency': 0.15     # Weight for data consistency
    }
    
    def __init__(self):
        """Initialize the confidence scorer."""
        self.review_threshold = 0.85  # Score below this triggers review
        
    def score_course(self, course: Course, institution: Institution) -> Dict[str, float]:
        """
        Calculate confidence scores for a single course.
        
        Args:
            course: Course to evaluate
            institution: Institution information
            
        Returns:
            Dictionary of confidence scores by category
        """
        scores = {}
        
        # Course code confidence
        scores['course_code'] = self._score_course_code(course.course_code)
        
        # Grade confidence
        scores['grade'] = self._score_grade(course.grade)
        
        # Credits confidence
        scores['credits'] = self._score_credits(
            course.credits,
            institution.credit_system
        )
        
        # Data completeness
        scores['completeness'] = self._score_completeness(course)
        
        # Data consistency
        scores['consistency'] = self._score_consistency(course)
        
        # Calculate weighted average
        total_score = sum(
            scores[k] * self.WEIGHTS[k]
            for k in scores
        )
        
        # Add final score
        scores['total'] = round(total_score, 2)
        
        # Log scoring details
        logger.debug(
            f"Course confidence scores: {course.course_code}",
            extra={'scores': scores}
        )
        
        return scores
    
    def _score_course_code(self, code: str) -> float:
        """
        Score course code validity and format.
        
        Args:
            code: Course code to evaluate
            
        Returns:
            Confidence score 0-1
        """
        if not code:
            return 0.0
            
        # Extract numeric part
        numbers = re.findall(r'\d+', code)
        if not numbers:
            return 0.5  # No number found
            
        try:
            level = int(numbers[0])
            
            # Sub-100 courses are valid but excluded
            if level < 100:
                return 1.0
                
            # Normal course range
            if 100 <= level <= 499:
                return 1.0
                
            # Graduate level
            if 500 <= level <= 999:
                return 1.0
                
            # Unusual course number
            return 0.7
            
        except ValueError:
            return 0.5
    
    def _score_grade(self, grade: str) -> float:
        """
        Score grade validity.
        
        Args:
            grade: Grade to evaluate
            
        Returns:
            Confidence score 0-1
        """
        if not grade:
            return 0.0
            
        grade = grade.upper()
        
        # Valid transferable grades
        if grade in self.VALID_GRADES:
            return 1.0
            
        # Non-transferable but valid grades
        if grade in {'S', 'P', 'CR', 'T'}:
            return 0.8
            
        # Failing grades
        if grade in {'F', 'W', 'I', 'U'}:
            return 0.9
            
        # Unknown grade format
        return 0.3
    
    def _score_credits(self, credits: float, system: str) -> float:
        """
        Score credit value validity.
        
        Args:
            credits: Credit value to evaluate
            system: Credit system (semester/quarter)
            
        Returns:
            Confidence score 0-1
        """
        if credits <= 0:
            return 0.0
            
        if system == "semester":
            # Most semester courses are 3-4 credits
            if 1 <= credits <= 6:
                return 1.0
            if credits < 1:
                return 0.7
            return 0.8
            
        elif system == "quarter":
            # Most quarter courses are 4-5 credits
            if 1 <= credits <= 8:
                return 1.0
            if credits < 1:
                return 0.7
            return 0.8
            
        return 0.5
    
    def _score_completeness(self, course: Course) -> float:
        """
        Score data completeness.
        
        Args:
            course: Course to evaluate
            
        Returns:
            Confidence score 0-1
        """
        required_fields = {
            'course_code': bool(course.course_code),
            'course_name': bool(course.course_name),
            'credits': course.credits > 0,
            'grade': bool(course.grade)
        }
        
        optional_fields = {
            'year': bool(course.year),
            'term': bool(course.term)
        }
        
        # Required fields are weighted more heavily
        required_score = sum(required_fields.values()) / len(required_fields)
        optional_score = sum(optional_fields.values()) / len(optional_fields)
        
        return round(required_score * 0.8 + optional_score * 0.2, 2)
    
    def _score_consistency(self, course: Course) -> float:
        """
        Score data consistency.
        
        Args:
            course: Course to evaluate
            
        Returns:
            Confidence score 0-1
        """
        score = 1.0
        
        # Check for inconsistencies
        if course.credits > 0 and course.grade in {'W', 'I'}:
            score -= 0.2
            
        if course.is_intro_course and course.credit_category == "Major":
            score -= 0.1
            
        if course.grade in {'F', 'W'} and not course.needs_review:
            score -= 0.2
            
        return max(0, score)
    
    def evaluate_transcript(
        self,
        evaluation: TranscriptEvaluation
    ) -> Dict[str, Dict[str, float]]:
        """
        Evaluate confidence for an entire transcript.
        
        Args:
            evaluation: TranscriptEvaluation to score
            
        Returns:
            Dictionary of course scores and overall confidence
        """
        results = {
            'courses': {},
            'overall': {},
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_courses': len(evaluation.courses),
                'credit_system': evaluation.institution.credit_system
            }
        }
        
        # Score each course
        total_score = 0
        needs_review = 0
        
        for course in evaluation.courses:
            scores = self.score_course(course, evaluation.institution)
            results['courses'][course.course_code] = scores
            total_score += scores['total']
            
            if scores['total'] < self.review_threshold:
                needs_review += 1
                course.needs_review = True
        
        # Calculate overall metrics
        if evaluation.courses:
            avg_score = total_score / len(evaluation.courses)
            results['overall'] = {
                'average_confidence': round(avg_score, 2),
                'courses_needing_review': needs_review,
                'review_percentage': round(
                    (needs_review / len(evaluation.courses)) * 100,
                    1
                )
            }
        
        # Log evaluation results
        logger.info(
            "Completed transcript confidence evaluation",
            extra={
                'overall_score': results['overall'].get('average_confidence'),
                'needs_review': needs_review
            }
        )
        
        return results

# Global scorer instance
scorer = ConfidenceScorer() 