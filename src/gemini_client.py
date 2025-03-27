import streamlit as st
import google.generativeai as genai
from .models import TranscriptKeyData
from typing import Dict


class GeminiClient:
    def __init__(self):
        self.llm = None

    def initialize(self) -> bool:
        """Initialize the Gemini models"""
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            generation_config= genai.GenerationConfig(temperature=0, response_mime_type = "application/json")
            self.llm = genai.GenerativeModel('gemini-1.5-pro', generation_config=generation_config)
            return True
        except Exception as e:
            st.error(f"Error initializing Gemini: {str(e)}")
            return False

    def process_transcript(self, pdf_content: bytes, filename: str) -> str:
        """Process PDF with Gemini Vision API"""
        try:
            prompt = """
            Extract ALL information from this transcript. If the data has watermark, please read grade, course code, course name, credits, grade, term, year, and transfer details carefully.
            If it's examination like AP, make sure you to include exam name, grade and year taken  in the `Course Information` section.
            
            For transfer credits:
            - Look for explicit mentions of "transfer", "transferred from", or similar phrases
            - Check for course codes or prefixes from other institutions
            - Look for any indicators in the transcript key that denote transfer credits
            - Pay attention to different institution names listed with courses
            
            For course codes:
            - Look for alphanumeric combinations in formats like:
            * MATH1310 (letters followed directly by numbers)
            * PEB 1138 (letters, space, then numbers)
            * SPAN 1301 (subject code followed by course number)
            - Course codes may appear before or after course names
            - Some codes may have spaces between letters and numbers, others may not

            For grades:
            - Look for letter grades (A, B, C, D, F) with optional +/- modifiers
            - Look for numerical grades (e.g., 4.0, 3.0)
            - Look for special grades (P/Pass, CR/Credit, W/Withdrawn)
            - Check for grades both after course details and in separate columns
            - Grade may appear after course name or on a separate line. Make sure you read the grade completely and correctly.


            For Year:
            - Look for the year the course was taken
            - Check for year after course details or in a separate column
            - Year may appear after course name or on a separate line. Make sure you read the year completely and correctly.
            - Year could be mentioned in the term as 16/FA which could mean 2016 Fall, extract 2016 as year

            For Term:
            - Look for the term the course was taken
            - Check for term after course details or in a separate column
            - Term may appear after course name or on a separate line. Make sure you read the term completely and correctly.
            - Term could be mentioned in the term as 16/FA which could mean 2016 Fall, extract 'Fall' as term

            
            Format it EXACTLY as shown below in json format. Do not add any extra information or change the format.:

            Student Information:
            Name: [student name]
            ID: [student id]
            Program: [program name if available]

            Institution Information:
            Name: [institution name]
            Location: [location]

            Course Information:
            [List every course with exactly this format, one course at a time:]
            Course Code: [Extract full course code including both letters and numbers, maintaining original spacing/format (e.g., "MATH1310" or "PEB 1138")]
            Course Name: [full course name]
            Credits: [number]
            Grade: [grade]
            Status: [status if available, e.g., "Active", "In Progress", "Withdrawn"]
            Term: [term if available]
            Year: [year if available]
            Is Transfer: [True if any of the courses listed on the transcripts are transferred from other institutions.
            You can use following conditions to verify if the course is transferred:
                         1. Course is explicitly marked as transferred
                         2. Course is from a different institution
                         3. Course has transfer credit indicators
                         4. Course appears in a transfer credit section
                         Otherwise, write False]
            Transfer Details: [transfer_details If the following condition is "True", include the source institution or program (e.g., "Transferred from XYZ College", "AP Credit"). Leave empty if not a transfer]
            [blank line between each course]
            [blank line between each course]

    
            """
            
            response = self.llm.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": pdf_content}]
            )
            
            return response.text
            
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
            
            response = self.llm.generate_content(
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


    def extract_policy_handbook(self, pdf_content: bytes) -> str:
        """Extract policy text from PDF using Gemini Vision"""
        try:
            prompt = """
            Extract the transfer credit policy text from this PDF. Focus on sections that discuss transferability, eligibility, and any specific conditions or clauses.
            Ensure to include all relevant details that would help in determining transfer credit eligibility.
            """
            
            response = self.llm.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": pdf_content}]
            )
            return response.text
            
        except Exception as e:
            st.error(f"Error extracting policy text: {str(e)}")
            return None
        
    def verify_with_policy_handbook(self, course_info: Dict, policy_text: str) -> Dict:
         # Construct a detailed prompt for Gemini
        prompt = f"""
        Transfer Credit Policy Verification:

        Course Details:
        - Course Name: {course_info.get('course_name', 'N/A')}
        - Course Code: {course_info.get('course_code', 'N/A')}
        - Institution: {course_info.get('source_institution', 'N/A')}
        - Year: {course_info.get('year', 'N/A')}
        - Term: {course_info.get('term', 'N/A')}
        - Grade/Status: {course_info.get('grade', course_info.get('status', 'N/A'))}

        Please analyze:
        1. Is this course eligible for transfer based on the policy?
        2. What specific policy clauses support or reject the transfer?
        3. Provide a confidence score for the recommendation (0-100%)
        
        Respond in a JSON format:
        {
            "is_transferable": true/false,
            "supporting_clauses": ["clause1", "clause2"],
            "confidence_score": 85,
            "additional_notes": "Optional detailed explanation"
        }

        Transfer Policy Text:
        {policy_text} 

        """

        try:
            verification_result = self.llm.generate_content(prompt)
            
            return {
                "policy_verified": True,
                "is_transferable": verification_result.get('is_transferable', False),
                "supporting_clauses": verification_result.get('supporting_clauses', []),
                "confidence_score": verification_result.get('confidence_score', 0),
                "additional_notes": verification_result.get('additional_notes', '')
            }
        except Exception as e:
            print(f"Error in policy verification: {e}")
            return {
                "policy_verified": False,
                "error": str(e)
            }