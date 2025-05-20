# display.py
import streamlit as st
import pandas as pd
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape,letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO


CREDIT_CATEGORIES = [
    "General Education", 
    "Major Requirement",
    "Major Elective",
    "Free Elective",
    "Core Requirement",
    "Minor Requirement",
    "Prerequisites",
    "Not Applicable"
]

def generate_pdf(data: Dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph("Transcript Analysis Report", title_style))
    elements.append(Spacer(1, 20))

    # Student Information
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

    # Course Information
    elements.append(Paragraph("Course Information", styles['Heading2']))
    
    courses = data.get('courses', [])
    if courses:
        # Include all fields from the DataFrame
        headers = [
            'Course Code', 'Course Name', 'Credits', 'Grade', 'Credit Category', 'Year', 'Is Transfer', 'Transfer Details', 
            'Source Institution', 'Source File', 'Notes'
        ]
        
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
                str(course.get('notes', ''))
            ])
            
        # Carefully balanced column widths for landscape mode (total ~ 750)
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
            55    # Notes
        ]
        course_table = Table(course_data, colWidths=col_widths)
        course_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),  # Smaller header font
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  # Less padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),   # Add top padding
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),     # Smaller content font
            ('LEFTPADDING', (0, 0), (-1, -1), 3),  # Less left padding
            ('RIGHTPADDING', (0, 0), (-1, -1), 3), # Less right padding
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Thinner grid lines
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),   # Center headers
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),    # Right align credits
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Left align course code
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Left align course name
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')     # Top align all cells
        ]))
        elements.append(course_table)

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def display_evaluation_results(evaluation_results: Dict):
    """
    Display comprehensive transfer credit evaluation results 
    with detailed insights and policy verification details
    """
    st.header("Transfer Credit Evaluation Results")
    
    # Summary metrics
    summary = evaluation_results.get('summary', {})
    col1, col2, col3 = st.columns(3)
    
    total_courses = summary.get('total_courses', 0)
    total_accepted = summary.get('transferable_courses', 0)
    total_credits = summary.get('total_credits', 0)
    total_accepted_credits = summary.get('total_transferable_credits', 0)
    total_rejected_credits = summary.get('total_rejected_credits', 0)

    
    with col1:
        st.metric("Total Credits Attempted", f"{total_credits:.1f}")
    with col2:
        st.metric("Total Credits Accepted", f"{total_accepted_credits:.1f}")
    with col3:
        acceptance_rate = (total_accepted_credits / total_credits * 100) if total_credits > 0 else 0.0
        st.metric("Credit Acceptance Rate", f"{acceptance_rate:.1f}%")

    # Display evaluated courses
    if evaluation_results.get('evaluated_courses'):
        st.subheader("Evaluated Courses")
        
        # Prepare courses data with policy verification details
        courses_data = []
        for course in evaluation_results['evaluated_courses']:
            course_entry = course.copy()
            courses_data.append(course_entry)
        
        # Create DataFrame
        df = pd.DataFrame(courses_data)
        
        # Calculate transfer status
        df['status'] = df.apply(
            lambda x: '✅ Accepted' if x['transferable'] 
            else f'❌ Rejected ({len(x["rejection_reasons"])} issues)',
            axis=1
        )
        
        # Display dataframe with enhanced configuration
        st.dataframe(
            df[[
                'course_code', 'course_name', 'credits', 
                'grade', 'status', 'rejection_reasons'
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
                    'Credits',
                    format="%.1f"
                ),
                'grade': st.column_config.TextColumn(
                    'Grade',
                    width='small'
                ),
                'status': st.column_config.TextColumn(
                    'Transfer Status',
                    width='medium'
                ),
                'rejection_reasons': st.column_config.TextColumn(
                    'Issues',
                    width='large'
                )
        
            })
        

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
    """Display combined results with evaluation"""
    try:
        
        # Create tabs for different sections of the display
        tabs = st.tabs(["Student & Course Info", "Transcript Key"])
        
        with tabs[0]:
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

            # Display courses
            st.header("All Courses")
            if data.get("courses"):
                courses_df = pd.DataFrame(data["courses"])
                courses_df['notes'] = courses_df.apply(validate_course, axis=1)

                if 'credit_category' not in courses_df.columns:
                    courses_df['credit_category'] = 'Not Applicable'
                
                # Define grade options
                grade_options = [
                    "A", "A-","A+", "B+", "B", "B-", "C+", "C", "C-", "S", "CR",
                    "D+", "D", "D-", "F", "P", "NP", "W", "I", 1, 2, 3, 4, 5
                ]

                # Convert is_transfer to boolean
                courses_df['is_transfer'] = courses_df['is_transfer'].fillna(True)
                courses_df['is_transfer'] = courses_df['is_transfer'].apply(lambda x: bool(x) if isinstance(x, (bool, int)) else x.lower() == 'true' if isinstance(x, str) else False)
                
                edited_df = st.data_editor(
                    courses_df,
                    num_rows="dynamic",
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
                        "credit_category": st.column_config.SelectboxColumn("Credit Category", help="Category of credit", options=CREDIT_CATEGORIES, required=True),
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
                issues = edited_df[edited_df['notes'] != "✓"]
                if not issues.empty:
                    st.warning(f"Found {len(issues)} courses with data quality issues")
                
        with tabs[1]:
            # Display transcript key information
            st.header("Transcript Key Information")
            if data.get("transcript_keys"):
                # Filter out transcript keys that don't have a source institution
                valid_keys = [key for key in data["transcript_keys"] if key.get("source_institution")]
                
                if valid_keys:
                    # Create tabs for different institutions
                    tab_titles = [key["source_institution"] for key in valid_keys]
                    institution_tabs = st.tabs(tab_titles)
                    
                    # Display each institution's key in its tab
                    for key_data, tab in zip(valid_keys, institution_tabs):
                        with tab:
                            display_institution_key(key_data)
                else:
                    st.warning("No valid transcript keys found with institution information")
            else:
                st.info("No transcript key information available")
                


        if st.button("Generate PDF"):
            pdf_data = generate_pdf({
                'student_info': data.get('student_info', {}),
                'courses': edited_df.to_dict('records')
            })
            st.download_button(
                "Download PDF",
                pdf_data,
                "transcript_analysis.pdf",
                "application/pdf"
            )            
        # Return edited dataframe if it exists
        return edited_df if 'edited_df' in locals() else None

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")
        with st.expander("Error Details"):
            st.write("Raw data structure:")
            st.json(data)
        return None

def display_institution_key(key_data):
    """Display transcript key information for a single institution"""
    
    # Display institution name
    st.subheader(f"{key_data['source_institution']} Grading System")
    st.write(key_data)
    
   