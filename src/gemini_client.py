import streamlit as st
from google import genai
from google.genai import types
from pathlib import Path
import tempfile
import json
import logging
from .models import Student
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)


class GeminiClient:
    """
    Gemini 2.x client using the **Google Gen AI** SDK.
    """
    #MODEL_NAME= "gemini-2.5-flash-preview-04-17"      # <— put the model you really need
    MODEL_NAME = "gemini-2.5-pro-preview-05-06"      # <— put the model you really need

    def __init__(self) -> None:
        self.client: Optional[genai.Client] = None
        self._base_config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=Student
        )

    # ---------- setup ----------
    def initialize(self) -> bool:
        try:
            self.client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
            return True
        except Exception as e:
            st.error(f"Gemini init error: {e}")
            return False

    # ---------- helpers ----------
    def _upload_pdf(self, pdf_bytes: bytes) -> types.File:
        """
        Upload a PDF and return its File handle for the 'contents' list.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        # Upload **once**; reuse the returned object for every call
        return self.client.files.upload(file=str(tmp_path))
    
    def _generate(self, prompt, file_or_part, config: Optional[types.GenerateContentConfig] = None):
        """
        Wraps client.models.generate_content with optional custom config.
        Defaults to self._base_config if none is provided.
        """
        return self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=[prompt, file_or_part],
            config=config or self._base_config,
        )
        r

    # ---------- transcript processing ----------
    def process_transcript(self, pdf_content: bytes, filename: str) -> str | None:
        """
        Extract course data from a transcript PDF.
        """
        try:
            prompt = """
            Extract the student, institution, and every course from this transcript PDF.
            Populate all required fields; leave optional ones null if unknown.
            """
            pdf_file = self._upload_pdf(pdf_content)
            resp = self._generate(prompt, pdf_file)
            if not resp.text:
                st.error("Gemini returned empty or invalid JSON")
                logging.warning(resp.text)          # raw text for debugging
                return None
            return resp.text           # JSON as string

        except Exception as e:
            st.error(f"Error processing {filename}: {e}")
            return None

    def extract_transcript_key(self, pdf_content: bytes, institution_name: str) :
        """Extract transcript key information using Gemini Vision"""
        if not institution_name:
            st.warning(f"No institution name provided for transcript key extraction")
            return None

        try:
            prompt = """
            You are reading the "transcript key" section of a U.S. college transcript.

            Extract and return ONLY the following 6 categories of information. Format them **exactly** as shown below, using only plain strings, dictionaries, and lists. Do NOT include any JSON Schema or metadata like {"type": "string"}.

            Return a single, valid JSON object in this exact format:

            {
            "source_institution": "Name of the institution as it appears in the transcript key",
            "grade_scales": {
                "A": "4.0",
                "B+": "3.3"
            },
            "credit_definitions": [
                "One semester credit hour equals 15 contact hours.",
                "Courses numbered 1000 and above carry degree credit."
            ],
            "special_notations": [
                "* indicates repeated course",
                "† indicates honors credit"
            ],
            "transfer_indicators": [
                "T = Transfer credit",
                "TR = Credit from another institution"
            ],
            "term_definitions": {
                "Fall": "August to December",
                "Spring": "January to May"
            }
            }

            ⚠️ DO NOT include:
            - nested objects like { "type": "string" }
            - extra fields
            - explanations or markdown
            - any nulls

            Only return the final JSON object exactly as shown, but populated with the actual data from the transcript key page.

            """
            pdf_file = self._upload_pdf(pdf_content)

            custom_config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json"
            )

            resp = self._generate(prompt, pdf_file, config=custom_config)

            key_data = resp.text
            key_data["source_institution"] = institution_name
            
            return key_data
            
        except Exception as e:
            st.error(f"Error extracting transcript key: {str(e)}")
            return None
        
    