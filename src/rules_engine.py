"""
Business Rules Engine Module

This module implements a flexible rules engine for transfer credit evaluation.
It provides:
1. Rule definition and management
2. Rule execution and chaining
3. Custom rule conditions
4. Rule priority handling
5. Rule audit logging

The engine allows for complex rule combinations while maintaining
clear documentation and traceability of decisions.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel
import logging

# Configure logging
logger = logging.getLogger(__name__)

class RuleType(Enum):
    """
    Types of transfer credit rules.
    
    Types:
    - GRADE: Grade requirements
    - CREDIT: Credit value rules
    - COURSE_MATCH: Course equivalency
    - INSTITUTION: Institution-specific rules
    - TIME_LIMIT: Time-based restrictions
    - PROGRAM: Program-specific requirements
    """
    GRADE = "grade"
    CREDIT = "credit"
    COURSE_MATCH = "course_match"
    INSTITUTION = "institution"
    TIME_LIMIT = "time_limit"
    PROGRAM = "program"

class RulePriority(Enum):
    """
    Rule execution priority levels.
    
    Priorities:
    - CRITICAL: Must be evaluated first
    - HIGH: Important but not critical
    - MEDIUM: Standard priority
    - LOW: Can be evaluated last
    """
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class RuleContext:
    """
    Context data for rule evaluation.
    
    Attributes:
        course_data (Dict): Course information
        student_data (Dict): Student information
        program_data (Dict): Program requirements
        evaluation_date (datetime): When evaluation occurs
    """
    course_data: Dict[str, Any]
    student_data: Dict[str, Any]
    program_data: Dict[str, Any]
    evaluation_date: datetime

class Rule(BaseModel):
    """
    Transfer credit evaluation rule.
    
    Attributes:
        id (str): Unique rule identifier
        name (str): Human-readable name
        description (str): Detailed rule description
        type (RuleType): Rule category
        priority (RulePriority): Execution priority
        condition (str): Rule condition in DSL format
        active (bool): Whether rule is currently active
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id: str
    name: str
    description: str
    type: RuleType
    priority: RulePriority
    condition: str
    active: bool = True
    created_at: datetime
    updated_at: datetime

class RuleResult(BaseModel):
    """
    Result of rule evaluation.
    
    Attributes:
        rule_id (str): ID of evaluated rule
        passed (bool): Whether rule passed
        message (str): Explanation of result
        details (Dict): Additional result data
    """
    rule_id: str
    passed: bool
    message: str
    details: Dict[str, Any] = {}

class RulesEngine:
    """
    Core rules engine implementation.
    
    This class handles:
    - Rule registration and management
    - Rule evaluation and chaining
    - Result aggregation
    - Audit logging
    """
    
    def __init__(self):
        """Initialize rules engine with empty rule set."""
        self._rules: Dict[str, Rule] = {}
        self._conditions: Dict[str, Callable] = {}
        
    def register_rule(self, rule: Rule) -> None:
        """
        Register a new rule in the engine.
        
        Args:
            rule (Rule): Rule to register
        """
        if rule.id in self._rules:
            logger.warning(f"Overwriting existing rule: {rule.id}")
        self._rules[rule.id] = rule
        logger.info(f"Registered rule: {rule.name} ({rule.id})")

    def register_condition(self, name: str, func: Callable) -> None:
        """
        Register a custom rule condition function.
        
        Args:
            name (str): Condition name
            func (Callable): Implementation function
        """
        self._conditions[name] = func
        logger.info(f"Registered condition: {name}")

    def evaluate_rule(self, rule: Rule, context: RuleContext) -> RuleResult:
        """
        Evaluate a single rule against provided context.
        
        Args:
            rule (Rule): Rule to evaluate
            context (RuleContext): Evaluation context
            
        Returns:
            RuleResult: Evaluation result
        """
        try:
            # Parse and evaluate rule condition
            condition_func = self._conditions.get(rule.condition)
            if not condition_func:
                return RuleResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"Unknown condition: {rule.condition}"
                )
            
            # Execute condition with context
            passed = condition_func(context)
            
            # Create detailed result
            return RuleResult(
                rule_id=rule.id,
                passed=passed,
                message=f"Rule {'passed' if passed else 'failed'}: {rule.name}",
                details={
                    "type": rule.type.value,
                    "priority": rule.priority.value,
                    "context": {
                        "course": context.course_data.get("course_code"),
                        "program": context.program_data.get("program_code"),
                        "evaluation_date": context.evaluation_date.isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {str(e)}")
            return RuleResult(
                rule_id=rule.id,
                passed=False,
                message=f"Evaluation error: {str(e)}"
            )

    def evaluate_all(self, context: RuleContext) -> List[RuleResult]:
        """
        Evaluate all active rules in priority order.
        
        Args:
            context (RuleContext): Evaluation context
            
        Returns:
            List[RuleResult]: All evaluation results
        """
        results = []
        
        # Get active rules sorted by priority
        active_rules = [r for r in self._rules.values() if r.active]
        sorted_rules = sorted(active_rules, key=lambda r: r.priority.value)
        
        # Evaluate each rule
        for rule in sorted_rules:
            result = self.evaluate_rule(rule, context)
            results.append(result)
            
            # Log result
            logger.info(
                f"Rule {rule.id} evaluation: "
                f"{'passed' if result.passed else 'failed'}"
            )
            
        return results

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """
        Get rule by ID.
        
        Args:
            rule_id (str): Rule identifier
            
        Returns:
            Optional[Rule]: Rule if found
        """
        return self._rules.get(rule_id)

    def get_rules_by_type(self, rule_type: RuleType) -> List[Rule]:
        """
        Get all rules of specified type.
        
        Args:
            rule_type (RuleType): Type to filter by
            
        Returns:
            List[Rule]: Matching rules
        """
        return [r for r in self._rules.values() if r.type == rule_type]

# Common rule conditions
def min_grade_condition(context: RuleContext) -> bool:
    """Check if course meets minimum grade requirement."""
    grade = context.course_data.get("grade", "")
    return grade in ["A", "A-", "B+", "B", "B-", "C+", "C"]

def credit_value_condition(context: RuleContext) -> bool:
    """Check if course has valid credit value."""
    credits = context.course_data.get("credits", 0)
    return 0 < credits <= 4

def time_limit_condition(context: RuleContext) -> bool:
    """Check if course is within time limit."""
    course_date = context.course_data.get("completion_date")
    if not course_date:
        return False
    years_old = (context.evaluation_date - course_date).days / 365
    return years_old <= 10

def institution_condition(context: RuleContext) -> bool:
    """Check if institution is approved."""
    institution = context.course_data.get("institution", "")
    return institution in context.program_data.get("approved_institutions", []) 