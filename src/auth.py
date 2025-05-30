"""
Authentication and Authorization Module

This module provides role-based access control (RBAC) for the transcript evaluation system.
It implements:
1. User roles and permissions
2. Access control checks
3. Permission validation
4. Session management

The module ensures that users can only access features appropriate to their role,
with special handling for administrative and evaluation functions.

Disabling Authentication for Development/Testing:
----------------------------------------------
To disable authentication:

1. Environment Setup (choose one method):
   ```bash
   # Method 1: Export in shell
   export APP_ENV=development
   export AUTH_ENABLED=false
   
   # Method 2: Add to .env file
   APP_ENV=development
   AUTH_ENABLED=false
   ```

2. Code Usage with Disabled Auth:
   ```python
   from src.auth import AuthManager, get_test_user
   
   # Initialize auth manager (will detect disabled auth)
   auth_manager = AuthManager()
   
   # Get test user (has admin privileges)
   test_user = get_test_user()
   
   # Create session (never expires when auth disabled)
   session = auth_manager.create_session(test_user)
   
   # All permission checks return True when auth disabled
   can_edit = auth_manager.check_permission(session.token, Permission.EDIT_EVALUATION)
   # can_edit will be True
   ```

3. Effects of Disabled Auth:
   - All permission checks return True
   - Test admin user available via get_test_user()
   - Sessions never expire
   - Warning logs indicate auth is disabled

4. Security Warning:
   - Never disable auth in production
   - Only use disabled auth for development/testing
   - Re-enable auth before deploying
"""

from enum import Enum
from typing import List, Set, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel
import logging
from .config import config

# Configure logging
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """
    User role definitions with associated permission levels.
    
    Roles:
    - ENROLLMENT: Basic access for enrollment counselors
    - TES: Transfer evaluation specialist with edit access
    - ADMIN: Full system access including configuration
    """
    ENROLLMENT = "enrollment"  # Basic view access
    TES = "tes"              # Evaluation specialist
    ADMIN = "admin"          # Full system access

class Permission(Enum):
    """
    Granular permissions for system features.
    
    Permissions:
    - VIEW_BASIC: View basic transcript data
    - VIEW_CONFIDENCE: View confidence scores
    - EDIT_EVALUATION: Modify evaluation results
    - MANAGE_RULES: Configure transfer rules
    - MANAGE_USERS: User administration
    """
    VIEW_BASIC = "view_basic"
    VIEW_CONFIDENCE = "view_confidence"
    EDIT_EVALUATION = "edit_evaluation"
    MANAGE_RULES = "manage_rules"
    MANAGE_USERS = "manage_users"

# Role to Permission mapping
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.ENROLLMENT: {
        Permission.VIEW_BASIC
    },
    UserRole.TES: {
        Permission.VIEW_BASIC,
        Permission.VIEW_CONFIDENCE,
        Permission.EDIT_EVALUATION
    },
    UserRole.ADMIN: {
        Permission.VIEW_BASIC,
        Permission.VIEW_CONFIDENCE,
        Permission.EDIT_EVALUATION,
        Permission.MANAGE_RULES,
        Permission.MANAGE_USERS
    }
}

class User(BaseModel):
    """
    User model with role-based permissions.
    
    Attributes:
        id (str): Unique user identifier
        email (str): User's email address
        name (str): User's full name
        role (UserRole): User's assigned role
        active (bool): Whether the user account is active
        last_login (datetime): Timestamp of last login
        
    Usage with Disabled Auth:
        When auth is disabled, all permission checks return True regardless of role.
        Use get_test_user() to get a pre-configured admin user for testing.
    """
    id: str
    email: str
    name: str
    role: UserRole
    active: bool = True
    last_login: Optional[datetime] = None

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission (Permission): Permission to check
            
        Returns:
            bool: True if user has the permission
        """
        # If auth is disabled, grant all permissions
        if not config.security.auth_enabled:
            return True
            
        if not self.active:
            return False
        return permission in ROLE_PERMISSIONS[self.role]

    def can_edit_evaluations(self) -> bool:
        """Check if user can edit evaluation results"""
        return self.has_permission(Permission.EDIT_EVALUATION)

    def can_view_confidence_scores(self) -> bool:
        """Check if user can view confidence metrics"""
        return self.has_permission(Permission.VIEW_CONFIDENCE)

    def can_manage_rules(self) -> bool:
        """Check if user can manage transfer rules"""
        return self.has_permission(Permission.MANAGE_RULES)

@dataclass
class Session:
    """
    User session data with JWT token management.
    
    Attributes:
        user (User): Active user
        token (str): JWT session token
        expires (datetime): Token expiration timestamp
    """
    user: User
    token: str
    expires: datetime

class AuthManager:
    """
    Authentication and session management.
    
    This class handles:
    - User authentication
    - Session creation and validation
    - Permission checking
    - Token management
    
    Usage with Disabled Auth:
    -----------------------
    1. Auth is automatically disabled if AUTH_ENABLED=false in environment
    2. All permission checks return True
    3. Sessions never expire
    4. Use get_test_user() for a pre-configured admin user
    
    Example:
        ```python
        auth_manager = AuthManager()  # Detects disabled auth from environment
        test_user = get_test_user()
        session = auth_manager.create_session(test_user)
        # All permission checks return True
        ```
    """
    
    def __init__(self):
        """Initialize auth manager."""
        self._secret_key = config.security.jwt_secret
        self._token_expiry = timedelta(hours=config.security.token_expiry_hours)
        self._active_sessions: dict[str, Session] = {}
        self._auth_enabled = config.security.auth_enabled
        
        if not self._auth_enabled:
            logger.warning(
                "Authentication is DISABLED. "
                "This should only be used for testing!"
            )

    def create_session(self, user: User) -> Session:
        """
        Create new user session with JWT token.
        
        Args:
            user (User): User to create session for
            
        Returns:
            Session: New session with token
        """
        # If auth is disabled, create a session that never expires
        if not self._auth_enabled:
            token = "disabled-auth-token"
            expires = datetime.utcnow() + timedelta(days=365)
            session = Session(user=user, token=token, expires=expires)
            self._active_sessions[token] = session
            return session
            
        expires = datetime.utcnow() + self._token_expiry
        token_data = {
            "user_id": user.id,
            "role": user.role.value,
            "exp": expires.timestamp()
        }
        token = jwt.encode(token_data, self._secret_key, algorithm="HS256")
        
        session = Session(user=user, token=token, expires=expires)
        self._active_sessions[token] = session
        return session

    def validate_token(self, token: str) -> Optional[Session]:
        """
        Validate JWT token and return associated session.
        
        Args:
            token (str): JWT token to validate
            
        Returns:
            Optional[Session]: Valid session or None
        """
        # If auth is disabled, always return the session
        if not self._auth_enabled:
            return self._active_sessions.get(token)
            
        try:
            # Verify token signature and expiration
            jwt.decode(token, self._secret_key, algorithms=["HS256"])
            
            # Check if session exists and is valid
            session = self._active_sessions.get(token)
            if session and datetime.utcnow() < session.expires:
                return session
                
        except jwt.InvalidTokenError:
            pass
            
        return None

    def end_session(self, token: str) -> None:
        """
        End user session and invalidate token.
        
        Args:
            token (str): Token of session to end
        """
        if token in self._active_sessions:
            del self._active_sessions[token]

    def check_permission(self, token: str, permission: Permission) -> bool:
        """
        Check if session has specific permission.
        
        Args:
            token (str): Session token
            permission (Permission): Permission to check
            
        Returns:
            bool: True if session has permission
        """
        # If auth is disabled, grant all permissions
        if not self._auth_enabled:
            return True
            
        session = self.validate_token(token)
        if not session:
            return False
        return session.user.has_permission(permission)

def get_test_user() -> User:
    """
    Create a test user with admin permissions.
    
    This function is primarily used when authentication is disabled
    for development or testing purposes.
    
    Returns:
        User: A pre-configured admin user with full permissions
        
    Usage:
        ```python
        # Get test user for development
        test_user = get_test_user()
        auth_manager = AuthManager()
        session = auth_manager.create_session(test_user)
        ```
        
    Note:
        Only use this in development/testing environments.
        The test user has full admin privileges.
    """
    return User(
        id="test-user",
        email="test@example.com",
        name="Test User",
        role=UserRole.ADMIN
    ) 