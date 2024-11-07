import streamlit as st
import pandas as pd
from typing import Dict
from .models import CombinedTranscriptData

def display_evaluation_results(evaluation_results: Dict):
    """Display transfer credit evaluation results"""
    st.header("Transfer Credit Evaluation Results")
    
    # Summary metrics
    summary = evaluation_results.get('summary', {})
    col1, col2, col3 = st.columns(3)
    
    total_attempted = summary.get('total_credits_attempted', 0)
    total_accepted = summary.get('total_credits_accepted', 0)
    
    with col1:
        st.metric(
            "Total Credits Attempted", 
            f"{total_attempted:.1f}"
        )
        
    with col2:
        st.metric(
            "Total Credits Accepted", 
            f"{total_accepted:.1f}"
        )
        
    with col3:
        # Calculate acceptance rate with zero division handling
        if total_attempted > 0:
            acceptance_rate = (total_accepted / total_attempted) * 100
        else:
            acceptance_rate = 0.0
        st.metric("Credit Acceptance Rate", f"{acceptance_rate:.1f}%")

    # Create tabs for different views
    tab1, tab2 = st.tabs(["Evaluated Courses", "Rejection Details"])
    
    with tab1:
        # Display evaluated courses
        if evaluation_results.get('evaluated_courses'):
            df = pd.DataFrame(evaluation_results['evaluated_courses'])
            
            # Calculate transfer status label
            df['status'] = df.apply(
                lambda x: '✅ Accepted' if x['transferable'] 
                else '❌ Rejected', axis=1
            )
            
            # Format rejection reasons
            df['rejection_reasons'] = df['rejection_reasons'].apply(
                lambda x: '\n'.join(x) if x else ''
            )
            
            # Display as an editable dataframe
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
                        'Rejection Reasons',
                        width='large'
                    )
                }
            )

    with tab2:
        rejected_courses = summary.get('rejected_courses', [])
        if rejected_courses:
            # List of rejected courses
            for course in rejected_courses:
                with st.expander(f"{course['course_code']} - {course['course_name']}"):
                    for reason in course.get('reasons', []):
                        st.write(f"- {reason}")
        else:
            st.success("No rejected courses found!")

def display_combined_results(data: Dict):
    """Display combined results with evaluation"""
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

        # Display courses
        st.header("All Courses")
        if data.get("courses"):
            courses_df = pd.DataFrame(data["courses"])
            
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
                },
                hide_index=True,
            )
            
            # Display basic statistics
            st.header("Basic Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Courses", len(edited_df))
                st.metric("Total Credits", f"{edited_df['credits'].sum():.1f}")
            with col2:
                transfer_courses = len(edited_df[edited_df['is_transfer'] == True])
                transfer_credits = edited_df[edited_df['is_transfer'] == True]['credits'].sum()
                st.metric("Transfer Courses", transfer_courses)
                st.metric("Transfer Credits", f"{transfer_credits:.1f}")
                
            return edited_df
        else:
            st.warning("No course data found")
            return None

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")
        with st.expander("Error Details"):
            st.write("Raw data structure:")
            st.json(data)
        return None