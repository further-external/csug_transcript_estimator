"""
Gemini AI Client Module

This module provides a client interface for Google's Gemini AI model,
specifically configured for transcript data extraction. It handles:
1. Model initialization and configuration
2. PDF file processing
3. Transcript data extraction
4. Response handling and error management

The client is designed to be lightweight and focused on the specific
needs of transcript processing, with configurable model parameters
and error handling.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

from google import genai
from google.genai import types
from google.api_core import exceptions, retry
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import Student  # Pydantic model for data validation
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Default extraction prompt
DEFAULT_PROMPT = """
Extract the following information from this transcript PDF:

1. Student Information:
   - Full name
   - Student ID (if present)
   - Program/Major
   - Academic level

2. Institution Information:
   - Institution name
   - Location
   - Accreditation info (if present)

3. Course Information (for each course):
   - Course code
   - Course name
   - Credits
   - Grade
   - Term/Year taken
   - Transfer status

Format the response as a JSON object with these exact keys:
{
    "student_info": {
        "name": string,
        "id": string or null,
        "program": string or null,
        "level": string or null
    },
    "institution_info": {
        "name": string,
        "location": string or null,
        "accreditation": string or null
    },
    "courses": [
        {
            "course_code": string,
            "course_name": string,
            "credits": number,
            "grade": string,
            "year": string or null,
            "term": string or null,
            "is_transfer": boolean
        }
    ]
}

Ensure all required fields are populated. Leave optional fields as null if not found.
"""

class GeminiError(Exception):
    """Base exception for Gemini client errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}
        logger.error(f"GeminiError: {message}", extra=self.details)

class APIKeyError(GeminiError):
    """Raised for API key related issues."""
    pass

class ModelError(GeminiError):
    """Raised for model-related issues."""
    pass

class ProcessingError(GeminiError):
    """Raised for content processing issues."""
    pass

class GeminiClient:
    """
    Lightweight client for interacting with Gemini 2.x AI models.
    
    This client is specifically configured for transcript processing with:
    - Zero-temperature response generation (deterministic)
    - JSON response formatting
    - Student schema validation
    - PDF file handling capabilities
    """

    # Latest Gemini model optimized for document processing
    DEFAULT_MODEL = "models/gemini-2.5-pro-preview-05-06"

    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        temperature: float = 0.0,
        response_mime_type: str = "application/json",
    ) -> None:
        """
        Initialize the Gemini client with configuration.
        
        Args:
            api_key (str): Google API key for Gemini access
            model_name (str, optional): Specific model to use
            temperature (float): Response randomness (0.0 = deterministic)
            response_mime_type (str): Expected response format
        """
        logger.info("Initializing GeminiClient")
        if not api_key:
            raise APIKeyError("API key cannot be empty")
            
        logger.info(f"Using model: {model_name or self.DEFAULT_MODEL}")
        self._api_key = api_key
        self.model_name = model_name or self.DEFAULT_MODEL
        self._base_config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=Student,
        )
        self._client: Optional[genai.Client] = None
        
        # Validate API key on initialization
        try:
            self._validate_api_key()
        except Exception as e:
            raise APIKeyError(f"Invalid API key: {str(e)}", {"error": str(e)})

    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry.retry_if_exception_type(
            (exceptions.ServiceUnavailable, exceptions.DeadlineExceeded)
        ),
        reraise=True
    )
    def _validate_api_key(self) -> None:
        """Validate API key by attempting to list models."""
        try:
            logger.info("Validating API key...")
            client = self._client_or_init()
            models = client.models.list()
            model_names = [
                m.name for m in models
                if "generateContent" in getattr(m, "supported_actions", [])
            ]
            if not model_names:
                raise ModelError("No models support content generation")
            if self.model_name not in model_names:
                logger.warning(f"Selected model {self.model_name} not found in available models")
            logger.info(f"Available models: {', '.join(model_names)}")
            
        except exceptions.PermissionDenied as e:
            raise APIKeyError("API key permission denied", {"error": str(e)})
        except exceptions.InvalidArgument as e:
            raise APIKeyError("Invalid API key format", {"error": str(e)})
        except Exception as e:
            raise GeminiError(f"API key validation failed: {str(e)}", {"error": str(e)})

    # ---------- Helper Methods ----------
    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry.retry_if_exception_type(
            (exceptions.ServiceUnavailable, exceptions.DeadlineExceeded)
        ),
        reraise=True
    )
    def _client_or_init(self) -> genai.Client:
        """
        Get existing client or create new one if needed.
        
        Returns:
            genai.Client: Initialized Gemini client
        
        This lazy initialization helps avoid unnecessary API connections.
        """
        if not self._client:
            logger.info("Creating new Gemini client")
            try:
                self._client = genai.Client(
                    api_key=self._api_key,
                    timeout=config.api_timeout
                )
                logger.info("Successfully initialized Gemini client")
            except Exception as e:
                raise GeminiError(f"Failed to initialize client: {str(e)}", {"error": str(e)})
        return self._client
    
    def list_models(self) -> list[str]:
        """
        List all available Gemini models that support content generation.
        
        Returns:
            list[str]: Names of available models
        """
        logger.info("Listing available models")
        client = self._client_or_init()
        models = client.models.list()
        model_list = [
            m.name for m in models
            if "generateContent" in getattr(m, "supported_actions", [])
        ]
        logger.info(f"Found {len(model_list)} available models")
        return model_list
 
    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry.retry_if_exception_type(
            (exceptions.ServiceUnavailable, exceptions.DeadlineExceeded)
        ),
        reraise=True
    )
    def _upload_pdf(self, client: genai.Client, pdf_bytes: bytes) -> Tuple[types.File, Path]:
        """
        Upload PDF data to Gemini for processing.
        
        Args:
            client (genai.Client): Active Gemini client
            pdf_bytes (bytes): Raw PDF file data
            
        Returns:
            Tuple[types.File, Path]: Gemini file object and temp file path
            
        Creates a temporary file to handle the upload process.
        """
        if not pdf_bytes:
            raise ProcessingError("Empty PDF data provided")
            
        logger.info(f"Creating temporary file for PDF upload ({len(pdf_bytes)} bytes)")
        tmp_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                tmp_path = Path(tmp.name)
                logger.info(f"Temporary file created at: {tmp_path}")
            
            try:
                logger.info("Uploading PDF to Gemini")
                file_obj = client.files.upload(file=str(tmp_path))
                logger.info("PDF upload successful")
                return file_obj, tmp_path
            except Exception as e:
                raise ProcessingError(f"PDF upload failed: {str(e)}", {
                    "error": str(e),
                    "file_size": len(pdf_bytes)
                })
        except Exception as e:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
            raise ProcessingError(f"Failed to process PDF: {str(e)}", {"error": str(e)})

    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry.retry_if_exception_type(
            (exceptions.ServiceUnavailable, exceptions.DeadlineExceeded)
        ),
        reraise=True
    )
    def _generate(
        self,
        prompt: str,
        file_or_part: Any,
        config: Optional[types.GenerateContentConfig] = None,
    ) -> types.GenerateContentResponse:
        """
        Generate content using the Gemini model.
        
        Args:
            prompt (str): Instruction prompt for the model
            file_or_part: File or content part to process
            config (GenerateContentConfig, optional): Custom configuration
            
        Returns:
            GenerateContentResponse: Model's response
            
        Raises:
            Exception: If content generation fails
        """
        client = self._client_or_init()
        start_time = time.time()
        
        try:
            logger.info(f"Generating content with model: {self.model_name}")
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, file_or_part],
                config=config or self._base_config,
            )
            
            if not response.text:
                raise ProcessingError("Empty response from model")
                
            # Log performance metrics
            duration = time.time() - start_time
            logger.info(
                "Content generation successful",
                extra={
                    "duration_seconds": duration,
                    "model": self.model_name,
                    "response_length": len(response.text)
                }
            )
            return response
            
        except exceptions.PermissionDenied as e:
            raise APIKeyError("Permission denied during generation", {"error": str(e)})
        except exceptions.InvalidArgument as e:
            raise ProcessingError(f"Invalid argument: {str(e)}", {"error": str(e)})
        except Exception as e:
            raise ProcessingError(f"Content generation failed: {str(e)}", {
                "error": str(e),
                "duration_seconds": time.time() - start_time
            })

    # ---------- Public Methods ----------
    def process_transcript(
        self,
        pdf_bytes: bytes,
        prompt: str | None = None,
    ) -> str | None:
        """
        Process a transcript PDF and extract structured data.
        
        Args:
            pdf_bytes (bytes): Raw PDF file data
            prompt (str, optional): Custom extraction prompt
            
        Returns:
            str | None: Extracted data as JSON string, or None on error
            
        The default prompt instructs the model to extract:
        - Student information
        - Institution details
        - Course listings
        All required fields must be populated, optional fields may be null.
        """
        prompt = prompt or DEFAULT_PROMPT
        temp_path = None
        start_time = time.time()
        
        try:
            logger.info("Starting transcript processing")
            pdf_file, temp_path = self._upload_pdf(self._client_or_init(), pdf_bytes)
            resp = self._generate(prompt, pdf_file)
            
            try:
                logger.info("Validating JSON response")
                json_data = json.loads(resp.text)
                
                # Validate required fields
                required_fields = ["student_info", "institution_info", "courses"]
                missing_fields = [f for f in required_fields if f not in json_data]
                if missing_fields:
                    raise ProcessingError(
                        f"Missing required fields: {', '.join(missing_fields)}",
                        {"missing_fields": missing_fields}
                    )
                
                # Log successful extraction with metrics
                duration = time.time() - start_time
                logger.info(
                    "Successfully extracted and validated transcript data",
                    extra={
                        "duration_seconds": duration,
                        "courses_count": len(json_data.get("courses", [])),
                        "response_size_bytes": len(resp.text)
                    }
                )
                return resp.text
                
            except json.JSONDecodeError as e:
                raise ProcessingError("Invalid JSON response", {
                    "error": str(e),
                    "response_text": resp.text[:100] + "..."  # Log truncated response
                })
                
        except GeminiError:
            raise  # Re-raise GeminiError exceptions
        except Exception as exc:
            raise ProcessingError(f"Unexpected error: {str(exc)}", {"error": str(exc)})
            
        finally:
            if temp_path and temp_path.exists():
                logger.info("Cleaning up temporary file")
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {str(e)}")

