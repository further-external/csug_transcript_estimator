"""
Configuration Module

This module manages application configuration and feature flags.
It provides:
1. Environment-based configuration
2. Feature flags
3. Security settings
4. Performance tuning

Configuration can be controlled via environment variables
or configuration files.

How to Disable Authentication for Development/Testing:
---------------------------------------------------
1. Set AUTH_ENABLED=false in your environment using any of these methods:
   - Export in shell: export AUTH_ENABLED=false
   - Add to .env file: AUTH_ENABLED=false
   - Set in Python: os.environ["AUTH_ENABLED"] = "false"

2. Make sure APP_ENV is not set to "production" as auth cannot be disabled in prod:
   - Export in shell: export APP_ENV=development
   - Add to .env file: APP_ENV=development
   - Set in Python: os.environ["APP_ENV"] = "development"

When auth is disabled:
- All permission checks return True
- A test admin user is automatically created
- Session tokens never expire
- Warning logs will indicate auth is disabled

Example .env file:
-----------------
APP_ENV=development
AUTH_ENABLED=false
JWT_SECRET=dev-secret-key
TOKEN_EXPIRY_HOURS=8
"""

import os
from typing import Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class SecurityConfig:
    """
    Security-related configuration.
    
    Attributes:
        auth_enabled (bool): Whether authentication is enabled. Set to False for development/testing.
            WARNING: Should always be True in production.
        jwt_secret (str): Secret for JWT signing
        token_expiry_hours (int): JWT token expiry in hours
        min_password_length (int): Minimum password length
        
    Usage:
        To disable auth for development:
        1. Set AUTH_ENABLED=false in environment or .env
        2. Ensure APP_ENV is not "production"
    """
    auth_enabled: bool = True
    jwt_secret: str = "default-secret-change-in-production"
    token_expiry_hours: int = 8
    min_password_length: int = 8

@dataclass
class CacheConfig:
    """
    Caching configuration.
    
    Attributes:
        enabled (bool): Whether caching is enabled
        redis_url (str): Redis connection URL
        default_ttl (int): Default cache TTL in seconds
    """
    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600

@dataclass
class RateLimitConfig:
    """
    Rate limiting configuration.
    
    Attributes:
        enabled (bool): Whether rate limiting is enabled
        default_rpm (int): Default requests per minute
        burst_size (int): Maximum burst size
    """
    enabled: bool = True
    default_rpm: int = 60
    burst_size: int = 10

class AppConfig:
    """
    Application configuration manager.
    
    This class provides:
    - Environment-based configuration
    - Feature flags
    - Configuration validation
    - Secure defaults
    """
    
    def __init__(self):
        """Initialize configuration with environment values."""
        self.environment = os.getenv("APP_ENV", "development")
        
        # Security configuration
        self.security = SecurityConfig(
            auth_enabled=self._parse_bool(
                os.getenv("AUTH_ENABLED", "true")
            ),
            jwt_secret=os.getenv(
                "JWT_SECRET",
                "default-secret-change-in-production"
            ),
            token_expiry_hours=int(
                os.getenv("TOKEN_EXPIRY_HOURS", "8")
            ),
            min_password_length=int(
                os.getenv("MIN_PASSWORD_LENGTH", "8")
            )
        )
        
        # Cache configuration
        self.cache = CacheConfig(
            enabled=self._parse_bool(
                os.getenv("CACHE_ENABLED", "true")
            ),
            redis_url=os.getenv(
                "REDIS_URL",
                "redis://localhost:6379"
            ),
            default_ttl=int(
                os.getenv("CACHE_TTL", "3600")
            )
        )
        
        # Rate limit configuration
        self.rate_limit = RateLimitConfig(
            enabled=self._parse_bool(
                os.getenv("RATE_LIMIT_ENABLED", "true")
            ),
            default_rpm=int(
                os.getenv("RATE_LIMIT_RPM", "60")
            ),
            burst_size=int(
                os.getenv("RATE_LIMIT_BURST", "10")
            )
        )
        
        # Validate configuration
        self._validate()
        
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean value."""
        return value.lower() in ("true", "1", "yes", "on")
        
    def _validate(self) -> None:
        """
        Validate configuration values.
        
        Important Security Checks:
        1. Prevents disabling auth in production
        2. Requires proper JWT secret in production
        3. Validates other security settings
        
        Raises:
            ValueError: If security configuration is invalid for environment
        """
        if self.environment == "production":
            # Ensure secure configuration in production
            if self.security.jwt_secret == "default-secret-change-in-production":
                raise ValueError("Default JWT secret not allowed in production")
                
            if not self.security.auth_enabled:
                raise ValueError(
                    "Authentication cannot be disabled in production. "
                    "To disable auth for development/testing, set APP_ENV to 'development' "
                    "or 'testing' and AUTH_ENABLED to 'false'"
                )
        
    def is_development(self) -> bool:
        """Check if in development environment."""
        return self.environment == "development"
        
    def is_production(self) -> bool:
        """Check if in production environment."""
        return self.environment == "production"
        
    def is_testing(self) -> bool:
        """Check if in testing environment."""
        return self.environment == "testing"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "environment": self.environment,
            "security": {
                "auth_enabled": self.security.auth_enabled,
                "token_expiry_hours": self.security.token_expiry_hours,
                "min_password_length": self.security.min_password_length
            },
            "cache": {
                "enabled": self.cache.enabled,
                "default_ttl": self.cache.default_ttl
            },
            "rate_limit": {
                "enabled": self.rate_limit.enabled,
                "default_rpm": self.rate_limit.default_rpm,
                "burst_size": self.rate_limit.burst_size
            }
        }

# Global configuration instance
config = AppConfig() 