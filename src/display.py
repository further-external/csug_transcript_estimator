# display.py
import streamlit as st
import pandas as pd
from typing import Dict, List
from .models import CombinedTranscriptData, TranscriptKeyData

def display_evaluation_results(evaluation_results: Dict):
    """Display transfer credit evaluation results with enhanced rejection details"""
    st.header("Transfer Credit Evaluation Results")
    
    # Summary metrics [Previous code remains unchanged]
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
        df = pd.DataFrame(evaluation_results['evaluated_courses'])
        
        # Calculate transfer status with detailed labels
        df['status'] = df.apply(
            lambda x: '✅ Accepted' if x['transferable'] 
            else f'❌ Rejected ({len(x["rejection_reasons"])} issues)',
            axis=1
        )
        
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
            }
        )

    # Enhanced rejected courses display
    rejected_courses = summary.get('rejected_courses', [])
    if rejected_courses:
        st.subheader("Rejected Courses Details")
        
        # Create detailed explanation mapping
        reason_explanations = {
            'Grade below minimum requirement': """
                The course grade does not meet the minimum requirements:
                - Undergraduate: C- or better
                - Graduate: B- or better
                Transfer credits must demonstrate sufficient mastery of the subject matter.
            """,
            'Credits exceed age limit': """
                The course was completed outside the acceptable timeframe:
                - Graduate: Must be within last 10 years
                - Undergraduate: No standard expiration
                This ensures knowledge is current and relevant.
            """,
            'Non-standard grade': """
                The grade format is not recognized or cannot be evaluated:
                - Standard letter grades (A through F)
                - Pass/Fail grades may have special requirements
                Clear grade documentation is required for evaluation.
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
                    To appeal this decision:
                    1. Submit additional documentation
                    2. Provide course syllabus
                    3. Request grade clarification
                    4. Demonstrate course equivalency
                """)
    else:
        st.success("No rejected courses found!")

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
                
                # Define grade options
                grade_options = [
                    "A", "A-", "B+", "B", "B-", "C+", "C", "C-", 
                    "D+", "D", "D-", "F", "P", "NP", "W", "I"
                ]
                
                # Define term options
                term_options = ["Fall", "Winter", "Spring", "Summer"]
                
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
                            "Transfer",
                            help="Is this a transfer course?",
                            default=False,
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