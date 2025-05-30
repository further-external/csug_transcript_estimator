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
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from .models import Student  # Pydantic model for data validation
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        self._api_key = api_key
        self.model_name = model_name or self.DEFAULT_MODEL
        self._base_config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=Student,
        )
        self._client: Optional[genai.Client] = None

    # ---------- Helper Methods ----------
    def _client_or_init(self) -> genai.Client:
        """
        Get existing client or create new one if needed.
        
        Returns:
            genai.Client: Initialized Gemini client
        
        This lazy initialization helps avoid unnecessary API connections.
        """
        if not self._client:
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Initialized Gemini client")
        return self._client
    
    def list_models(self) -> list[str]:
        """
        List all available Gemini models that support content generation.
        
        Returns:
            list[str]: Names of available models
        """
        client = self._client_or_init()
        models = client.models.list()
        return [
            m.name for m in models
            if "generateContent" in getattr(m, "supported_actions", [])
        ]
 
    @staticmethod
    def _upload_pdf(client: genai.Client, pdf_bytes: bytes) -> types.File:
        """
        Upload PDF data to Gemini for processing.
        
        Args:
            client (genai.Client): Active Gemini client
            pdf_bytes (bytes): Raw PDF file data
            
        Returns:
            types.File: Gemini file object for processing
            
        Creates a temporary file to handle the upload process.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)
        return client.files.upload(file=str(tmp_path))

    def _generate(
        self,
        prompt: str,
        file_or_part,
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
        """
        client = self._client_or_init()
        return client.models.generate_content(
            model=self.model_name,
            contents=[prompt, file_or_part],
            config=config or self._base_config,
        )

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
        prompt = prompt or (
            "Extract the student, institution, and every course from this transcript "
            "PDF. Populate all required fields; leave optional ones null if unknown."
        )
        try:
            pdf_file = self._upload_pdf(self._client_or_init(), pdf_bytes)
            resp = self._generate(prompt, pdf_file)
            return resp.text or None
        except Exception as exc:
            logger.exception("Error extracting transcript: %s", exc)
            return None

