
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

import google.genai as genai
# from google import genai
from google.genai import types

from .models import Student  # your Pydantic model
import streamlit as st

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GeminiClient:
    """Lightweight Gemini 2.x client."""

    DEFAULT_MODEL = "models/gemini-2.5-pro-preview-05-06"

    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        temperature: float = 0.0,
        response_mime_type: str = "application/json",
    ) -> None:
        self._api_key = api_key
        self.model_name = model_name or self.DEFAULT_MODEL
        self._base_config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=Student,
        )
        self._client: Optional[genai.Client] = None

    # ---------- helpers ----------
    def _client_or_init(self) -> genai.Client:
        if not self._client:
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Initialized Gemini client")
        return self._client
    

    def list_models(self) -> list[str]:
        """List all available models."""
        client = self._client_or_init()
        models =  client.models.list()
        return [
            m.name for m in models
            if "generateContent" in getattr(m, "supported_actions", [])
        ]
 
    @staticmethod
    def _upload_pdf(client: genai.Client, pdf_bytes: bytes) -> types.File:
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
        client = self._client_or_init()
        return client.models.generate_content(
            model=self.model_name,
            contents=[prompt, file_or_part],
            config=config or self._base_config,
        )

    # ---------- public helpers ----------
    def process_transcript(
        self,
        pdf_bytes: bytes,
        prompt: str | None = None,
    ) -> str | None:
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

