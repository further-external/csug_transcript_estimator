"""
Display Module

This module handles the presentation of transcript evaluation results through:
1. Interactive Streamlit UI components
2. PDF report generation
3. Data validation feedback

The module provides:
- Summary statistics display
- Detailed course listings
- PDF report generation
- Data validation feedback
- Interactive data editing capabilities

The display is designed to be user-friendly while providing all necessary
information for both quick review and detailed analysis.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

# Credit categories for course classification
CREDIT_CATEGORIES = [
    "General Education",    # Core general education requirements
    "Major Requirement",    # Required courses for major
    "Major Elective",      # Elective courses within major
    "Free Elective",       # Any elective course
    "Core Requirement",    # Core curriculum requirements
    "Minor Requirement",   # Required courses for minor
    "Prerequisites",       # Prerequisite courses
    "Not Applicable"       # Credits that don't apply to program
]

def generate_pdf(data: Dict) -> bytes:
    """
    Generate a PDF report of transcript evaluation results.
    
    Creates a professional PDF report containing:
    - Student information
    - Course evaluations
    - Transfer credit summary
    - Confidence scores
    
    Args:
        data (Dict): Complete evaluation data including student info and courses
        
    Returns:
        bytes: PDF file contents as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = []

    # Create title with custom style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph("Transcript Analysis Report", title_style))
    elements.append(Spacer(1, 20))

    # Add student information section
    elements.append(Paragraph("Student Information", styles['Heading2']))
    student_data = [[k, v] for k, v in data.get('student_info', {}).items()]
    if student_data:
        student_table = Table(student_data)
        student_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(student_table)
        elements.append(Spacer(1, 20))

    # Add course information section
    elements.append(Paragraph("Course Information", styles['Heading2']))
    courses = data.get('courses', [])
    if courses:
        # Define table headers
        headers = [
            'Course Code', 'Course Name', 'Credits', 'Grade', 'Credit Category', 
            'Year', 'Is Transfer', 'Transfer Details', 'Source Institution', 
            'Source File', 'Confidence Score', 'Status', 'Notes'
        ]
        
        # Prepare course data
        course_data = [headers]
        for course in courses:
            course_data.append([
                str(course.get('course_code', '')),
                str(course.get('course_name', '')),
                str(course.get('credits', '')),
                str(course.get('grade', '')),
                str(course.get('credit_category', 'Not Applicable')),
                str(course.get('year', '')),
                'Yes' if course.get('is_transfer') else 'No',
                str(course.get('transfer_details', '')),
                str(course.get('source_institution', '')),
                str(course.get('source_file', '')),
                f"{course.get('confidence_score', 0)}%",
                'Needs Review' if course.get('needs_review') else 
                ('Accepted' if course.get('transferable') else 'Rejected'),
                str(course.get('notes', ''))
            ])
            
        # Define column widths for readability
        col_widths = [
            70,   # Course Code
            140,  # Course Name
            35,   # Credits
            35,   # Grade
            70,   # Credit Category
            35,   # Year
            45,   # Is Transfer
            90,   # Transfer Details
            70,   # Source Institution
            60,   # Source File
            50,   # Confidence Score
            50,   # Status
            55    # Notes
        ]
        
        # Create and style course table
        course_table = Table(course_data, colWidths=col_widths)
        course_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            # Content styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            # Alignment
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        elements.append(course_table)

    # Generate PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def display_evaluation_results(evaluation_results: Dict, is_quarter: bool = False):
    """
    Display transcript evaluation results in the Streamlit UI.
    
    Shows:
    - Summary metrics
    - High-confidence course evaluations
    - Low-confidence courses needing review
    - Detailed course information
    
    Args:
        evaluation_results (Dict): Complete evaluation results
    """
    st.header("Transfer Credit Evaluation Results")
    
    # Display summary metrics in columns
    summary = evaluation_results.get('summary', {})
    col1, col2, col3, col4 = st.columns(4)
    
    total_credits = summary.get('total_credits', 0)
    total_accepted_credits = summary.get('total_transferable_credits', 0)
    total_rejected_credits = summary.get('total_rejected_credits', 0)
    low_confidence_credits = summary.get('low_confidence_credits', 0)
    
    with col1:
        st.metric("Total Credits", f"{total_credits:.1f}")
    with col2:
        st.metric("Accepted Credits", f"{total_accepted_credits:.1f}")
    with col3:
        st.metric("Rejected Credits", f"{total_rejected_credits:.1f}")
    with col4:
        st.metric("Low Confidence Credits", f"{low_confidence_credits:.1f}")

    # Display evaluated courses
    if evaluation_results.get('evaluated_courses'):
        # Show high confidence courses
        st.subheader("Evaluated Courses")
        high_confidence_courses = [
            course for course in evaluation_results['evaluated_courses']
            if not course.get('needs_review', False)
        ]
        
        if high_confidence_courses:
            df_high = pd.DataFrame(high_confidence_courses)
            df_high['status'] = df_high.apply(
                lambda x: '✅ Accepted' if x['transferable']
                else f'❌ Rejected ({len(x["rejection_reasons"])} issues)',
                axis=1
            )
            
            st.dataframe(
                df_high[[
                    'course_code', 'course_name', 'credits',
                    'grade', 'confidence_score', 'status', 'rejection_reasons'
                ]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'course_code': st.column_config.TextColumn(
                        'Course Code',
                        width='medium'
                    ),
                    'course_name': st.column_config.TextColumn(
                        'Course Name',
                        width='large'
                    ),
                    'credits': st.column_config.NumberColumn(
                        'Credits (adjusted)' if is_quarter else 'Credits',
                        format="%.1f"
                    ),
                    'grade': st.column_config.TextColumn(
                        'Grade',
                        width='small'
                    ),
                    'confidence_score': st.column_config.NumberColumn(
                        'Confidence Score',
                        format="%.1f%%"
                    ),
                    'status': st.column_config.TextColumn(
                        'Transfer Status',
                        width='medium'
                    ),
                    'rejection_reasons': st.column_config.TextColumn(
                        'Issues',
                        width='large'
                    )
                }
            )
        
        # Show low confidence courses
        low_confidence_courses = [
            course for course in evaluation_results['evaluated_courses']
            if course.get('needs_review', False)
        ]
        
        if low_confidence_courses:
            st.subheader("Courses Needing Review")
            st.warning(
                f"{len(low_confidence_courses)} courses could not be evaluated "
                "with high confidence and require manual review."
            )
            
            df_low = pd.DataFrame(low_confidence_courses)
            st.dataframe(
                df_low[[
                    'course_code', 'course_name', 'credits',
                    'grade', 'confidence_score', 'rejection_reasons'
                ]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'course_code': st.column_config.TextColumn(
                        'Course Code',
                        width='medium'
                    ),
                    'course_name': st.column_config.TextColumn(
                        'Course Name',
                        width='large'
                    ),
                    'credits': st.column_config.NumberColumn(
                        'Credits (adjusted)' if is_quarter else 'Credits',
                        format="%.1f"
                    ),
                    'grade': st.column_config.TextColumn(
                        'Grade',
                        width='small'
                    ),
                    'confidence_score': st.column_config.NumberColumn(
                        'Confidence Score',
                        format="%.1f%%"
                    ),
                    'rejection_reasons': st.column_config.TextColumn(
                        'Issues',
                        width='large'
                    )
                }
            )
            if is_quarter:
                st.caption("🛈 *Credits shown are adjusted to semester equivalents (÷1.5) due to Quarter system selection.*")

            if summary.get('total_transferable_credits', 0) >= 90:
                st.warning("Accepted credits have reached the maximum transferable limit of 90.")

def validate_course(course):
    """Validate course data and return any issues"""
    notes = []
    
    # Check required fields
    if not course.get('course_code'): notes.append("Missing code")
    if not course.get('course_name'): notes.append("Missing name")
    if not course.get('credits'): notes.append("Missing credits")
    if not course.get('year'): notes.append("Missing Year")
    if not course.get('grade'): notes.append("Missing grade")
    if not course.get('source_institution'): notes.append("Missing institution")
    
    # Check data quality
    credits = course.get('credits', 0)
    if credits and (credits < 0 or credits > 12):
        notes.append("Unusual credits")
    
    valid_grades = ["A", "A-", "A+", "B+", "B", "B-", "C+", "C", "C-", 
                   "D+", "D", "D-", "F", "P", "NP", "W", "I"]
    if course.get('grade') and course['grade'] not in valid_grades:
        notes.append("Non-standard grade")
        
    return ", ".join(notes) if notes else "✓"

def display_combined_results(data: Dict):
    """
    Display combined transcript data with editing capabilities.
    
    Provides:
    - Student information display
    - Institution information display
    - Editable course data grid
    - PDF report generation
    - Data validation feedback
    
    Args:
        data (Dict): Combined transcript data
        
    Returns:
        DataFrame or None: Edited course data if successful
    """
    try:
        # Display student information
        st.header("Student Information")
        if data.get("student_info"):
            student_df = pd.DataFrame([data["student_info"]])
            st.dataframe(student_df)
        else:
            st.warning("No student information found")

        # Display institutions
        st.header("Institutions")
        if data.get("institutions"):
            institutions_df = pd.DataFrame(data["institutions"])
            st.dataframe(institutions_df)
        else:
            st.warning("No institution information found")

        # Display editable course data
        st.header("All Courses")
        if data.get("courses"):
            courses_df = pd.DataFrame(data["courses"])
            courses_df['notes'] = courses_df.apply(validate_course, axis=1)

            if 'credit_category' not in courses_df.columns:
                courses_df['credit_category'] = 'Not Applicable'
            
            # Define valid grade options
            grade_options = [
                "A", "A-","A+", "B+", "B", "B-", "C+", "C", "C-", "S", "CR",
                "D+", "D", "D-", "F", "P", "NP", "W", "I"
            ]

            # Handle transfer status
            courses_df['is_transfer'] = courses_df['is_transfer'].fillna(True)
            courses_df['is_transfer'] = courses_df['is_transfer'].apply(
                lambda x: bool(x) if isinstance(x, (bool, int)) 
                else x.lower() == 'true' if isinstance(x, str) else False
            )
            
            # Disable editing for now, save this for later rev use
            # Create editable data grid
            # edited_df = st.data_editor(
            #     courses_df,
            #     num_rows="dynamic",
            #     use_container_width=True,

            # Create static results grid
            st.dataframe(
                courses_df,
                use_container_width=True,
                column_config={
                    "course_code": st.column_config.TextColumn(
                        "Course Code",
                        help="The course code/number",
                        required=True,
                    ),
                    "course_name": st.column_config.TextColumn(
                        "Course Name",
                        help="The full name of the course",
                        required=True,
                    ),
                    "credits": st.column_config.NumberColumn(
                        "Credits",
                        help="Number of credits",
                        min_value=0,
                        max_value=12,
                        step=0.5,
                        required=True,
                        format="%.1f",
                    ),
                    "credit_category": st.column_config.SelectboxColumn(
                        "Credit Category",
                        help="Category of credit",
                        options=CREDIT_CATEGORIES,
                        required=True
                    ),
                    "grade": st.column_config.SelectboxColumn(
                        "Grade",
                        help="Course grade",
                        options=grade_options,
                        required=True,
                    ),
                    "year": st.column_config.TextColumn(
                        "Year",
                        help="Academic year",
                        required=False,
                    ),
                    "is_transfer": st.column_config.CheckboxColumn(
                        "Is Transfer",
                        help="Is this a transfer course?",
                        default=False,
                    ),
                    "transfer_details": st.column_config.TextColumn(
                        "Transfer Details",
                        help="Transfer Details",
                    ),
                    "source_institution": st.column_config.TextColumn(
                        "Institution",
                        help="Source institution",
                        required=False,
                    ),
                    "source_file": st.column_config.TextColumn(
                        "Source File",
                        help="Original transcript file",
                        required=False,
                    ),
                    "notes": st.column_config.TextColumn(
                        "Validation Notes",
                        help="Data quality issues",
                        required=False,
                    ),
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="Status",
                        required=False,
                    ),
                },
                hide_index=True,
            )
            
            # Show validation issues
            issues = courses_df[courses_df['notes'] != "✓"]  # Changed refs from edited_df
            if not issues.empty:
                st.warning(f"Found {len(issues)} courses with data quality issues")

            # Add PDF generation option
            if st.button("Generate PDF"):
                pdf_data = generate_pdf({
                    'student_info': data.get('student_info', {}),
                    'courses': courses_df.to_dict('records')  # Changed ref from edited_df
                })
                st.download_button(
                    "Download PDF",
                    pdf_data,
                    "transcript_analysis.pdf",
                    "application/pdf"
                )            
            # return edited_df if 'edited_df' in locals() else None  # Remove for now
            return None

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")
        with st.expander("Error Details"):
            st.write("Raw data structure:")
            st.json(data)
        return None


    
   