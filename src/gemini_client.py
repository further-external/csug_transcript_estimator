import streamlit as st
from google import genai
from google.genai import types
from pathlib import Path
import tempfile
import json
import logging
from .models import Student, TranscriptKeyData
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

    def _generate(self, prompt, file_or_part):
        """
        Wraps client.models.generate_content with default config.
        """
        return self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=[prompt, file_or_part],
            config=self._base_config,
        )
    

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

    def extract_transcript_key(self, pdf_content: bytes, institution_name: str) -> TranscriptKeyData:
        """Extract transcript key information using Gemini Vision"""
        if not institution_name:
            st.warning(f"No institution name provided for transcript key extraction")
            return None

        try:
            prompt = """
            Extract and categorize ALL transcript key or grading system information into EXACTLY these categories:

            Grade Scales:
            [List each grade and its meaning/value/points, e.g., A = 4.0, B+ = 3.3]

            Credit Definitions:
            [List all credit-related definitions and rules]

            Special Notations:
            [List all special symbols, marks, or annotations used]

            Transfer Credit Indicators:
            [List all indicators used for transfer credits]

            Term Definitions:
            [List all academic terms and their definitions]
            """

            pdf_file = self._upload_pdf(pdf_content)
            resp = self._generate(prompt, pdf_file)
            
            key_data = self._parse_transcript_key(resp.text)
            key_data["source_institution"] = institution_name
            
            return key_data
            
        except Exception as e:
            st.error(f"Error extracting transcript key: {str(e)}")
            return None
        
    def _parse_transcript_key(self, text: str) -> TranscriptKeyData:
        """Parse transcript key text into structured data"""
        key_data = {
            "source_institution": "",
            "grade_scales": {},
            "credit_definitions": [],
            "special_notations": [],
            "transfer_indicators": [],
            "term_definitions": {}
        }
        
        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            lower_line = line.lower()
            if "grade scales:" in lower_line:
                current_section = "grade_scales"
            elif "credit definitions:" in lower_line:
                current_section = "credit_definitions"
            elif "special notations:" in lower_line:
                current_section = "special_notations"
            elif "transfer credit indicators:" in lower_line:
                current_section = "transfer_indicators"
            elif "term definitions:" in lower_line:
                current_section = "term_definitions"
            else:
                self._process_line(line, current_section, key_data)
                
        return key_data

    def _process_line(self, line: str, section: str, key_data: dict):
        """Process a single line of transcript key data"""
        if not section:
            return
            
        if section == "grade_scales":
            if "=" in line or ":" in line:
                separator = "=" if "=" in line else ":"
                grade, definition = line.split(separator, 1)
                key_data["grade_scales"][grade.strip()] = definition.strip()
                
        elif section == "term_definitions":
            if "=" in line or ":" in line:
                separator = "=" if "=" in line else ":"
                term, definition = line.split(separator, 1)
                key_data["term_definitions"][term.strip()] = definition.strip()
                
        elif section in ["credit_definitions", "special_notations", "transfer_indicators"]:
            cleaned_line = line.lstrip("•-*").strip()
            if cleaned_line:
                key_data[section].append(cleaned_line)