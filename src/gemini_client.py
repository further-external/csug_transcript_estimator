import streamlit as st
import google.generativeai as genai
from .models import TranscriptKeyData

# gemini_client.py
import streamlit as st
import google.generativeai as genai
from .models import TranscriptKeyData

class GeminiClient:
    def __init__(self):
        self.vision_model = None
        self.text_model = None

    def initialize(self) -> bool:
        """Initialize the Gemini models"""
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            self.text_model = genai.GenerativeModel('gemini-1.5-pro')
            self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
            return True
        except Exception as e:
            st.error(f"Error initializing Gemini: {str(e)}")
            return False

    def process_transcript(self, pdf_content: bytes, filename: str) -> str:
        """Process PDF with Gemini Vision API"""
        try:
            prompt = """
            Extract ALL information from this transcript.
            If it's examination like AP, make sure you to include exam name, grade and year taken  in the `Course Information` section.
            
            For transfer credits:
            - Look for explicit mentions of "transfer", "transferred from", or similar phrases
            - Check for course codes or prefixes from other institutions
            - Look for any indicators in the transcript key that denote transfer credits
            - Pay attention to different institution names listed with courses
            
            
            Format it EXACTLY as shown below:

            Student Information:
            Name: [student name]
            ID: [student id]
            Program: [program name if available]

            Institution Information:
            Name: [institution name]
            Location: [location]

            Course Information:
            [List every course with exactly this format, one course at a time:]
            Course Code: [exact code]
            Course Name: [full course name]
            Credits: [number]
            Grade: [grade]
            Term: [term if available]
            Year: [year if available]
            Is Transfer: [Write True ONLY if ANY of these conditions are met:
                         1. Course is explicitly marked as transferred
                         2. Course is from a different institution
                         3. Course has transfer credit indicators
                         4. Course appears in a transfer credit section
                         Otherwise, write False]
            Transfer Details: [transfer_details If Is Transfer is "Yes", include the source institution or program (e.g., "Transferred from XYZ College", "AP Credit"). Leave empty if not a transfer]
            [blank line between each course]
            [blank line between each course]

    
            """
            
            response = self.vision_model.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": pdf_content}]
            )
            
            return response.text
            
        except Exception as e:
            st.error(f"Error processing {filename}: {str(e)}")
            return None
        
    def extract_transcript_key(self, pdf_content: bytes, filename: str, institution_name: str) -> TranscriptKeyData:
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
            
            response = self.vision_model.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": pdf_content}]
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