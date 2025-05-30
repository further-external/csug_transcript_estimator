"""
Audit Logging Module

This module implements comprehensive audit logging for system activities.
It provides:
1. Structured activity logging
2. User action tracking
3. Data change history
4. Security event logging
5. Compliance reporting

The audit system ensures traceability and accountability for all
system operations, supporting compliance requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json
import logging
import uuid

# Configure logging
logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """
    Types of audit events.
    
    Types:
    - USER_ACCESS: User authentication events
    - DATA_ACCESS: Data retrieval events
    - DATA_CHANGE: Data modification events
    - SYSTEM_CONFIG: System configuration changes
    - SECURITY: Security-related events
    - EVALUATION: Transfer credit evaluations
    """
    USER_ACCESS = "user_access"
    DATA_ACCESS = "data_access"
    DATA_CHANGE = "data_change"
    SYSTEM_CONFIG = "system_config"
    SECURITY = "security"
    EVALUATION = "evaluation"

class AuditSeverity(Enum):
    """
    Severity levels for audit events.
    
    Levels:
    - INFO: Normal operations
    - WARNING: Potential issues
    - ERROR: Operation failures
    - CRITICAL: Security incidents
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """
    Audit event record.
    
    Attributes:
        id (str): Unique event identifier
        timestamp (datetime): When event occurred
        event_type (AuditEventType): Type of event
        severity (AuditSeverity): Event severity
        user_id (str): User who triggered event
        action (str): Action performed
        resource (str): Resource affected
        details (Dict): Additional event details
        metadata (Dict): System metadata
    """
    id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    metadata: Dict[str, Any]

class AuditLogger:
    """
    Core audit logging implementation.
    
    This class handles:
    - Event recording
    - Log persistence
    - Query capabilities
    - Report generation
    """
    
    def __init__(
        self,
        log_file: str,
        max_history: int = 10000,
        enable_console: bool = True
    ):
        """
        Initialize audit logger.
        
        Args:
            log_file (str): Path to audit log file
            max_history (int): Maximum events to retain
            enable_console (bool): Log to console
        """
        self._log_file = log_file
        self._max_history = max_history
        self._enable_console = enable_console
        self._events: List[AuditEvent] = []
        
        # Configure file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        )
        logger.addHandler(file_handler)
        
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'
                )
            )
            logger.addHandler(console_handler)
            
    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: str,
        action: str,
        resource: str,
        details: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> AuditEvent:
        """
        Record new audit event.
        
        Args:
            event_type (AuditEventType): Type of event
            severity (AuditSeverity): Event severity
            user_id (str): User identifier
            action (str): Action description
            resource (str): Affected resource
            details (Dict): Event details
            metadata (Dict): System metadata
            
        Returns:
            AuditEvent: Recorded event
        """
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
            metadata=metadata or {}
        )
        
        # Add to history
        self._events.append(event)
        if len(self._events) > self._max_history:
            self._events.pop(0)
            
        # Log to file/console
        log_message = (
            f"{event.event_type.value} - {event.action} - "
            f"User: {event.user_id} - Resource: {event.resource}"
        )
        
        if event.severity == AuditSeverity.CRITICAL:
            logger.critical(log_message, extra=event.details)
        elif event.severity == AuditSeverity.ERROR:
            logger.error(log_message, extra=event.details)
        elif event.severity == AuditSeverity.WARNING:
            logger.warning(log_message, extra=event.details)
        else:
            logger.info(log_message, extra=event.details)
            
        return event
        
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AuditEvent]:
        """
        Query audit events with filters.
        
        Args:
            event_type (AuditEventType): Filter by type
            severity (AuditSeverity): Filter by severity
            user_id (str): Filter by user
            resource (str): Filter by resource
            start_time (datetime): Filter by start time
            end_time (datetime): Filter by end time
            
        Returns:
            List[AuditEvent]: Matching events
        """
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
            
        if severity:
            events = [e for e in events if e.severity == severity]
            
        if user_id:
            events = [e for e in events if e.user_id == user_id]
            
        if resource:
            events = [e for e in events if e.resource == resource]
            
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
            
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
            
        return events
        
    def generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
        include_types: Optional[List[AuditEventType]] = None,
        min_severity: Optional[AuditSeverity] = None
    ) -> Dict[str, Any]:
        """
        Generate audit report for time period.
        
        Args:
            start_time (datetime): Report start time
            end_time (datetime): Report end time
            include_types (List[AuditEventType]): Event types to include
            min_severity (AuditSeverity): Minimum severity level
            
        Returns:
            Dict: Report data
        """
        events = self.get_events(start_time=start_time, end_time=end_time)
        
        if include_types:
            events = [e for e in events if e.event_type in include_types]
            
        if min_severity:
            events = [
                e for e in events
                if e.severity.value >= min_severity.value
            ]
            
        # Compile statistics
        total_events = len(events)
        events_by_type = {}
        events_by_severity = {}
        events_by_user = {}
        
        for event in events:
            # Count by type
            type_key = event.event_type.value
            events_by_type[type_key] = events_by_type.get(type_key, 0) + 1
            
            # Count by severity
            sev_key = event.severity.value
            events_by_severity[sev_key] = events_by_severity.get(sev_key, 0) + 1
            
            # Count by user
            events_by_user[event.user_id] = events_by_user.get(
                event.user_id, 0
            ) + 1
            
        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_events": total_events,
            "by_type": events_by_type,
            "by_severity": events_by_severity,
            "by_user": events_by_user,
            "events": [
                {
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.event_type.value,
                    "severity": e.severity.value,
                    "user_id": e.user_id,
                    "action": e.action,
                    "resource": e.resource,
                    "details": e.details
                }
                for e in events
            ]
        }

def log_data_access(
    logger: AuditLogger,
    user_id: str,
    resource: str,
    access_type: str,
    details: Dict[str, Any] = None
):
    """
    Log data access event.
    
    Args:
        logger (AuditLogger): Audit logger
        user_id (str): User accessing data
        resource (str): Resource accessed
        access_type (str): Type of access
        details (Dict): Access details
    """
    logger.log_event(
        event_type=AuditEventType.DATA_ACCESS,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        action=f"Data {access_type}",
        resource=resource,
        details=details
    )

def log_data_change(
    logger: AuditLogger,
    user_id: str,
    resource: str,
    change_type: str,
    old_value: Any,
    new_value: Any,
    details: Dict[str, Any] = None
):
    """
    Log data change event.
    
    Args:
        logger (AuditLogger): Audit logger
        user_id (str): User making change
        resource (str): Changed resource
        change_type (str): Type of change
        old_value (Any): Previous value
        new_value (Any): New value
        details (Dict): Change details
    """
    logger.log_event(
        event_type=AuditEventType.DATA_CHANGE,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        action=f"Data {change_type}",
        resource=resource,
        details={
            **(details or {}),
            "old_value": old_value,
            "new_value": new_value
        }
    )

def log_security_event(
    logger: AuditLogger,
    user_id: str,
    event_name: str,
    severity: AuditSeverity,
    details: Dict[str, Any] = None
):
    """
    Log security-related event.
    
    Args:
        logger (AuditLogger): Audit logger
        user_id (str): Associated user
        event_name (str): Security event name
        severity (AuditSeverity): Event severity
        details (Dict): Event details
    """
    logger.log_event(
        event_type=AuditEventType.SECURITY,
        severity=severity,
        user_id=user_id,
        action=event_name,
        resource="security",
        details=details
    ) 