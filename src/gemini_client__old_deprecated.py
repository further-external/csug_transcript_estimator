import streamlit as st
from google import genai
from google.genai import types
from .models import TranscriptKeyData
from typing import Dict
import json
import logging
from .models import Student

logging.basicConfig(level=logging.INFO)


class GeminiClient:
    def __init__(self):
        self.llm = None
        self.generate_config = None

    def initialize(self) -> bool:
        """Initialize the Gemini models"""
        try:
            client = genai.Client(
                vertexai=True,
                project="ai-transcript-438020",
                location="us-central1",
            )
            self.generate_config = types.GenerateContentConfig(
                temperature=0,
                top_p=0.95,
                max_output_tokens=20000,
                response_modalities=["TEXT"],
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
                ],
                response_mime_type = "application/json",
                response_schema=Student,
            )
            #genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            self.llm = client
            return True
        except Exception as e:
            st.error(f"Error initializing Gemini: {str(e)}")
            return False

    def process_transcript(self, pdf_content: bytes, filename: str) -> str:
        """Process PDF with Gemini Vision API"""
        try:
            prompt = """
            You are an expert transcript data extractor. Your task is to accurately extract information from student transcripts and format it into a structured JSON output.

            Instructions:

            1. Extract all information from the transcript.
            2. If the transcript has a watermark, pay extra attention to the grade, course code, course name, credits, year, and transfer details to ensure accurate extraction.
            3. **Course Information Extraction:**
            * Extract the following information for each course:
                * Course Code: Extract the full course code, maintaining the original spacing and format (e.g., "MATH1310", "PEB 1138", "SPAN 1301").
                * Course Name: Extract the full course name.
                * Credits: Extract the number of credits.
                * Grade: Extract the grade. Look for letter grades (A, B, C, D, F) with optional +/- modifiers, numerical grades, or special grades.
                * Status: Extract the course status if available (e.g., "Active", "In Progress", "Withdrawn").
                * Year: Extract the year the course was taken.
                * Is Transfer: Determine if the course is a transfer credit.
                * Transfer Details: If "Is Transfer" is true, include the source institution or program.
            4. **Student Information Extraction:**
            * Extract the student's name, ID, and program name (if available).
            5. **Institution Information Extraction:**
            * Extract the institution's name and location.

            Return the extracted data as a structured JSON that follows the Student model with Institution and Course objects.
                        """
            document = types.Part.from_bytes(
                data=pdf_content, mime_type="application/pdf",
            )
            contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Please process the attached transcript."),
                document  # This is already a Part object from from_uri()
                ]
             )
            ]
            response= self.llm.models.generate_content(
          model='gemini-2.5-pro-preview-05-06',
          contents=contents,
          config=self.generate_config,
          )
            
            return response.candidates[0].content.parts[0].text
            
        except Exception as e:
            st.error(f"Error processing {filename}: {str(e)}")
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

            document = types.Part.from_bytes(
                data=pdf_content, mime_type="application/pdf",
            )
            contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Please process the attached transcript."),
                document  # This is already a Part object from from_uri()
                ]
             )
            ]
            
            
            response= self.llm.models.generate_content(
            model='gemini-2.5-pro-preview-05-06',
            contents=contents,
            config=self.generate_config,
            )
                
            
            key_data = self._parse_transcript_key(response.text)
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

