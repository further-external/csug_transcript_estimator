"""
Configuration Module

This module handles all configuration settings for the application,
including logging, environment variables, and system settings.

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
import logging.config
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory for all logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Create dated log files
current_date = datetime.now().strftime("%Y-%m-%d")
ERROR_LOG = LOG_DIR / f"error_{current_date}.log"
DEBUG_LOG = LOG_DIR / f"debug_{current_date}.log"
API_LOG = LOG_DIR / f"api_{current_date}.log"

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "%(asctime)s | %(levelname)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": str(ERROR_LOG),
            "mode": "a",
        },
        "debug_file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(DEBUG_LOG),
            "mode": "a",
        },
        "api_file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(API_LOG),
            "mode": "a",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "error_file"],
            "level": "INFO",
            "propagate": True,
        },
        "gemini_client": {
            "handlers": ["api_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app": {
            "handlers": ["debug_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Initialize logging configuration
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

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

class Config:
    """Application configuration management."""
    
    def __init__(self):
        """Initialize configuration with environment variables and defaults."""
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        self.api_timeout = int(os.getenv("API_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "10"))
        
        # Confidence thresholds
        self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.7"))
        self.review_threshold = float(os.getenv("REVIEW_THRESHOLD", "0.85"))
        
        # Rate limiting
        self.rate_limit = int(os.getenv("RATE_LIMIT", "100"))
        self.rate_window = int(os.getenv("RATE_WINDOW", "3600"))
        
        # Cache settings
        self.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
        self.max_cache_size = int(os.getenv("MAX_CACHE_SIZE", "1000"))
        
        logger.info("Configuration initialized")
        if self.debug_mode:
            logger.debug(f"Current configuration: {self.to_dict()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "debug_mode": self.debug_mode,
            "api_timeout": self.api_timeout,
            "max_retries": self.max_retries,
            "batch_size": self.batch_size,
            "min_confidence": self.min_confidence,
            "review_threshold": self.review_threshold,
            "rate_limit": self.rate_limit,
            "rate_window": self.rate_window,
            "cache_ttl": self.cache_ttl,
            "max_cache_size": self.max_cache_size,
        }
    
    def validate(self) -> None:
        """Validate configuration settings."""
        try:
            assert 0 < self.api_timeout <= 120, "API timeout must be between 1 and 120 seconds"
            assert 0 < self.max_retries <= 5, "Max retries must be between 1 and 5"
            assert 0 < self.batch_size <= 100, "Batch size must be between 1 and 100"
            assert 0 <= self.min_confidence <= 1, "Minimum confidence must be between 0 and 1"
            assert 0 <= self.review_threshold <= 1, "Review threshold must be between 0 and 1"
            assert self.min_confidence <= self.review_threshold, "Minimum confidence must be less than review threshold"
            logger.info("Configuration validation successful")
        except AssertionError as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            raise ValueError(f"Invalid configuration: {str(e)}")

# Global configuration instance
config = Config()
config.validate() 