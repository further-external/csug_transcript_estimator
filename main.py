# main.py
import streamlit as st
from src.gemini_client import GeminiClient
from src.processors import process_multiple_pdfs, combine_transcript_data
from src.display import display_combined_results, display_evaluation_results
from src.evaluator import create_evaluator

def render_upload_tab(client):
    """Render the Upload & Process tab content"""
    st.header("Upload & Process Transcripts")

    # File upload section
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Choose PDF files", 
            type="pdf",
            accept_multiple_files=True
        )
        if uploaded_files:
            st.write(f"{len(uploaded_files)} file(s) uploaded successfully")
            
            if st.button("Process Transcripts", key="process_button"):
                with st.spinner("Processing transcripts..."):
                    try:
                        # Use the process_multiple_pdfs function which now handles transcript key extraction
                        results = process_multiple_pdfs(client, uploaded_files)
                        
                        if results:
                            st.session_state.processed_data = results
                            st.success(f"Successfully processed {len(results)} transcripts")
                            
                            combined_data = combine_transcript_data(results)
                            print(combined_data)
                            if combined_data:
                                st.session_state.combined_data = combined_data
                                st.success("Data combination complete!")
                                st.session_state.evaluation_complete = False
                            else:
                                st.error("Failed to combine transcript data")
                        else:
                            st.error("No results from transcript processing")
                            
                    except Exception as e:
                        st.error(f"Error during processing: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())

    with col2:
        st.info("""
        ### Upload Guidelines
        - Ensure transcripts are official and unlocked
        - Verify student name matches records
        - Include all pages of transcript
        """)

    # Show processed data in subtabs if available
    if st.session_state.get('combined_data'):
        edited_df = display_combined_results(st.session_state.combined_data)
        if edited_df is not None:
            st.session_state.combined_data['courses'] = edited_df.to_dict('records')

def render_review_tab():
    """Render the Review & Evaluate tab content"""
    st.header("Evaluate Transfer Credits")
    
    if not st.session_state.get('combined_data'):
        st.warning("Please upload and process transcripts in the Upload tab first")
        return

    # Evaluation controls
    if st.button("Start Evaluation", key="evaluate_button"):
        with st.spinner("Evaluating transfer credits..."):
            try:
                # Get program level from settings
                program_level = st.session_state.get('settings', {}).get('program_level', 'undergraduate')
                
                # Create evaluator and process results
                evaluator = create_evaluator(program_level=program_level)
                evaluation_results = evaluator.evaluate_transcript(st.session_state.combined_data)
                
                # Store evaluation results and set flag
                st.session_state.evaluation_results = evaluation_results
                st.session_state.evaluation_complete = True
            except Exception as e:
                st.error(f"Error during evaluation: {str(e)}")
                st.session_state.evaluation_complete = False

    # Display evaluation results if available
    if st.session_state.evaluation_complete and hasattr(st.session_state, 'evaluation_results'):
        display_evaluation_results(st.session_state.evaluation_results)

def render_settings_tab():
    """Render the Settings tab content"""
    st.header("Evaluation Settings")
    
    # Initialize settings in session state if not present
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'program_level': 'undergraduate',
            'max_elective_credits': 60.0,
            'credit_age_limit_years': 10,
            'min_grade_undergraduate': 'C-',
            'min_grade_graduate': 'B-',
            'max_major_transfer_percentage': 50.0
        }
    
    # Program Level
    st.session_state.settings['program_level'] = st.selectbox(
        "Program Level",
        options=['undergraduate', 'graduate'],
        index=0 if st.session_state.settings['program_level'] == 'undergraduate' else 1
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Maximum Elective Credits
        st.session_state.settings['max_elective_credits'] = st.number_input(
            "Maximum Elective Credits",
            min_value=0.0,
            max_value=120.0,
            value=float(st.session_state.settings['max_elective_credits']),
            step=0.5
        )
        
        # Credit Age Limit
        st.session_state.settings['credit_age_limit_years'] = st.number_input(
            "Credit Age Limit (Years)",
            min_value=0,
            max_value=20,
            value=int(st.session_state.settings['credit_age_limit_years'])
        )
    
    with col2:
        # Minimum Grades
        st.session_state.settings['min_grade_undergraduate'] = st.selectbox(
            "Minimum Undergraduate Grade",
            options=['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-'],
            index=['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-'].index(
                st.session_state.settings['min_grade_undergraduate']
            )
        )
        
        st.session_state.settings['min_grade_graduate'] = st.selectbox(
            "Minimum Graduate Grade",
            options=['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-'],
            index=['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-'].index(
                st.session_state.settings['min_grade_graduate']
            )
        )
    
    # Maximum Major Transfer Percentage
    st.session_state.settings['max_major_transfer_percentage'] = st.slider(
        "Maximum Major Transfer Percentage",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.settings['max_major_transfer_percentage']),
        step=5.0
    )
    
    # Save settings button
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")

def main():
    st.title("Transcript Analyzer")
    
    # Initialize session state
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'combined_data' not in st.session_state:
        st.session_state.combined_data = None
    if 'evaluation_complete' not in st.session_state:
        st.session_state.evaluation_complete = False

    # Initialize Gemini client
    client = GeminiClient()
    if not client.initialize():
        st.error("Failed to initialize Gemini client")
        return

    # Create main tabs
    upload_tab, review_tab, settings_tab = st.tabs([
        "Upload & Process",
        "Review & Evaluate",
        "Settings"
    ])

    # Render content for each tab
    with upload_tab:
        render_upload_tab(client)
        
    with review_tab:
        render_review_tab()
        
    with settings_tab:
        render_settings_tab()

if __name__ == "__main__":
    main()