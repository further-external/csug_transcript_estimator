# display.py
import streamlit as st
import pandas as pd
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape,letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from .models import TranscriptKeyData
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
            'Course Code', 'Course Name', 'Credits', 'Grade', 'Credit Category',
            'Term', 'Year', 'Is Transfer', 'Transfer Details', 
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
                str(course.get('term', '')),
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
            45,   # Term
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
    
    total_attempted = summary.get('total_credits_attempted', 0)
    total_accepted = summary.get('total_credits_accepted', 0)
    
    with col1:
        st.metric("Total Credits Attempted", f"{total_attempted:.1f}")
    with col2:
        st.metric("Total Credits Accepted", f"{total_accepted:.1f}")
    with col3:
        acceptance_rate = (total_accepted / total_attempted * 100) if total_attempted > 0 else 0.0
        st.metric("Credit Acceptance Rate", f"{acceptance_rate:.1f}%")

    # Display evaluated courses
    if evaluation_results.get('evaluated_courses'):
        st.subheader("Evaluated Courses")
        
        # Prepare courses data with policy verification details
        courses_data = []
        for course in evaluation_results['evaluated_courses']:
            course_entry = course.copy()
            
            # Add policy verification details
            policy_ver = course.get('transfer_policy_verification', {})
            course_entry['transfer_policy_verified'] = (
                '✅ Verified' if policy_ver.get('transfer_policy_verified') 
                else '❌ Not Verified'
            )
            course_entry['policy_confidence'] = policy_ver.get('confidence_score', 'N/A')
            course_entry['policy_supporting_clauses'] = ', '.join(
                policy_ver.get('supporting_clauses', [])
            )
            
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
                'grade', 'status', 'rejection_reasons',
                'transfer_policy_verified', 'policy_confidence', 
                'policy_supporting_clauses'
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
                ),
                'transfer_policy_verified': st.column_config.TextColumn(
                    'Policy Verification',
                    width='medium'
                ),
                'policy_confidence': st.column_config.TextColumn(
                    'Confidence',
                    width='small'
                ),
                'policy_supporting_clauses': st.column_config.TextColumn(
                    'Supporting Policy Clauses',
                    width='large'
                )
            }
        )

    # Policy Verification Summary
    policy_summary = summary.get('policy_verification_summary', {})
    if policy_summary.get('total_verified_courses', 0) > 0:
        st.subheader("Policy Verification Insights")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Verified Courses", 
                policy_summary.get('total_verified_courses', 0)
            )
        with col2:
            st.metric(
                "Policy Exceptions", 
                policy_summary.get('total_policy_exceptions', 0)
            )
        with col3:
            exception_rate = (
                policy_summary.get('total_policy_exceptions', 0) / 
                policy_summary.get('total_verified_courses', 1) * 100
            )
            st.metric("Exception Rate", f"{exception_rate:.1f}%")
        
        # Detailed Policy Verification
        if policy_summary.get('verified_courses_details'):
            st.subheader("Detailed Policy Verification")
            
            for course_detail in policy_summary['verified_courses_details']:
                with st.expander(f"{course_detail['course_code']} - {course_detail.get('course_name', 'Unknown')}"):
                    # Transferability Status
                    status_color = "green" if course_detail['is_transferable'] else "red"
                    st.markdown(f"**Transferability:** <span style='color:{status_color}'>{'Transferable' if course_detail['is_transferable'] else 'Not Transferable'}</span>", unsafe_allow_html=True)
                    
                    # Confidence Score
                    st.write(f"**Confidence Score:** {course_detail.get('confidence_score', 'N/A')}")
                    
                    # Supporting Policy Clauses
                    if course_detail.get('supporting_clauses'):
                        st.markdown("**Supporting Policy Clauses:**")
                        for clause in course_detail['supporting_clauses']:
                            st.markdown(f"- {clause}")
                    
                    # Additional Notes
                    if course_detail.get('additional_notes'):
                        st.info(f"**Additional Notes:** {course_detail['additional_notes']}")

    # Rejected Courses Section
    rejected_courses = summary.get('rejected_courses', [])
    if rejected_courses:
        st.subheader("Rejected Courses Details")
        
        # Reason explanations
        reason_explanations = {
            'Grade or status below requirement': """
                Course grade does not meet minimum requirements:
                - Undergraduate: Minimum grade of C-
                - Graduate: Minimum grade of B-
                Demonstrates insufficient mastery of subject matter.
            """,
            'Credits exceed age limit': """
                Course completed outside acceptable timeframe:
                - Typically within 10 years for relevance
                - Ensures currency of knowledge
                Older credits may require additional review
            """,
            'Failed policy verification': """
                Course did not meet specific institutional transfer policies:
                - Content may not align with program requirements
                - Insufficient course equivalency
                - Specialized policy constraints
            """
        }
        
        for course in rejected_courses:
            with st.expander(f"{course['course_code']} - {course['course_name']}"):
                for reason in course.get('reasons', []):
                    st.markdown(f"**Issue:** {reason}")
                    if explanation := reason_explanations.get(reason):
                        st.markdown("**Explanation:**")
                        st.markdown(explanation.strip())
                    st.markdown("---")
                
                st.info("""
                    Appeal Process:
                    1. Submit comprehensive documentation
                    2. Provide detailed course syllabus
                    3. Request formal grade clarification
                    4. Demonstrate course equivalency
                """)
    else:
        st.success("No courses were rejected during the transfer evaluation.")

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
    
    valid_grades = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", 
                   "D+", "D", "D-", "F", "P", "NP", "W", "I"]
    if course.get('grade') and course['grade'] not in valid_grades:
        notes.append("Non-standard grade")
        
    return ", ".join(notes) if notes else "✓"

def display_combined_results(data: Dict):
    """Display combined results with evaluation"""
    try:
        
        # Create tabs for different sections of the display
        tabs = st.tabs(["Student & Course Info", "Transcript Key", "Basic Statistics"])
        
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
                    "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "S",
                    "D+", "D", "D-", "F", "P", "NP", "W", "I", 1, 2, 3, 4, 5
                ]
                
                # Define term options
                term_options = ["Fall", "Winter", "Spring", "Summer"]

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
                        "term": st.column_config.SelectboxColumn(
                            "Term",
                            help="Academic term",
                            options=term_options,
                            required=False,
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
                
        with tabs[2]:
            # Display basic statistics
            st.header("Basic Statistics")
            col1, col2 = st.columns(2)
            
            # Calculate statistics based on edited_df if available
            if 'edited_df' in locals():
                with col1:
                    st.metric("Total Courses", len(edited_df))
                    st.metric("Total Credits", f"{edited_df['credits'].sum():.1f}")
                with col2:
                    transfer_courses = len(edited_df[edited_df['is_transfer'] == True])
                    transfer_credits = edited_df[edited_df['is_transfer'] == True]['credits'].sum()
                    st.metric("Transfer Courses", transfer_courses)
                    st.metric("Transfer Credits", f"{transfer_credits:.1f}")
            

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

def display_transcript_key(transcript_keys: List[TranscriptKeyData]):
    """Display transcript key information"""
    if not transcript_keys:
        st.info("No transcript key information available")
        return
        
    # Filter out transcript keys that don't have a source institution
    valid_keys = [key for key in transcript_keys if key.get("source_institution")]
    
    if not valid_keys:
        st.warning("No valid transcript keys found with institution information")
        return
        
    # Create tabs for different institutions if multiple keys exist
    if len(valid_keys) > 1:
        tab_titles = [key["source_institution"] for key in valid_keys]
        tabs = st.tabs(tab_titles)
        
        # Display each institution's key in its tab
        for key_data, tab in zip(valid_keys, tabs):
            with tab:
                display_institution_key(key_data)
    else:
        # Single institution - use container
        with st.container():
            display_institution_key(valid_keys[0])

def display_institution_key(key_data: TranscriptKeyData):
    """Display transcript key information for a single institution"""
    
    # Display institution name
    st.subheader(f"{key_data['source_institution']} Grading System")
    
    # Create columns for different types of information
    col1, col2 = st.columns(2)
    
    with col1:
        # Grade Scales
        if key_data.get("grade_scales"):
            st.write("##### Grade Scales")
            grade_df = pd.DataFrame(
                [(k, v) for k, v in key_data["grade_scales"].items()],
                columns=["Grade", "Definition"]
            )
            st.dataframe(grade_df, hide_index=True)
        
        # Term Definitions
        if key_data.get("term_definitions"):
            st.write("##### Term Definitions")
            term_df = pd.DataFrame(
                [(k, v) for k, v in key_data["term_definitions"].items()],
                columns=["Term", "Definition"]
            )
            st.dataframe(term_df, hide_index=True)
    
    with col2:
        # Credit Definitions
        if key_data.get("credit_definitions"):
            st.write("##### Credit Definitions")
            for definition in key_data["credit_definitions"]:
                st.write(f"• {definition}")
        
        # Special Notations
        if key_data.get("special_notations"):
            st.write("##### Special Notations")
            for notation in key_data["special_notations"]:
                st.write(f"• {notation}")
        
        # Transfer Indicators
        if key_data.get("transfer_indicators"):
            st.write("##### Transfer Credit Indicators")
            for indicator in key_data["transfer_indicators"]:
                st.write(f"• {indicator}")