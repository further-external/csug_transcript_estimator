import streamlit as st
import google.generativeai as genai

class GeminiClient:
    def __init__(self):
        self.vision_model = None
        self.text_model = None

    def initialize(self) -> bool:
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
            Extract ALL information from this transcript and format it EXACTLY as shown below:

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
            [blank line between each course]

            Important:
            - Extract EVERY course shown
            - Keep exact course codes and full names
            - Include ALL transfer courses
            - Show each course separately with all available fields
            - Put a blank line between courses
            - Do not summarize or combine courses
            """
            
            response = self.vision_model.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": pdf_content}]
            )
            
            """             
            with st.expander(f"Raw Response for {filename}"):
                st.text(response.text) 
            """
            
            return response.text
            
        except Exception as e:
            st.error(f"Error processing {filename}: {str(e)}")
            return None