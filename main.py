import streamlit as st
from src.gemini_client import GeminiClient
from src.processors import process_multiple_pdfs, combine_transcript_data
from src.display import display_combined_results, display_evaluation_results
from src.evaluator import create_evaluator


def process_uploaded_files(client, uploaded_files):
    """Process uploaded transcript files"""
    if st.button("Process Transcripts"):
            with st.spinner("Processing transcripts..."):
                try:
                    results = process_multiple_pdfs(client, uploaded_files)
                    
                    if results:
                        st.session_state.processed_data = results
                        st.success(f"Successfully processed {len(results)} transcripts")
                        
                        combined_data = combine_transcript_data(results)
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

def main():
    st.title("Transcript Analyzer")
    st.write("Upload multiple transcript PDFs for combined analysis")

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

    # File uploader
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Choose PDF files", 
            type="pdf",
            accept_multiple_files=True
        )
        if uploaded_files:
            st.write(f"{len(uploaded_files)} file(s) uploaded successfully")
            process_uploaded_files(client,uploaded_files)

    with col2:
        st.info("""
        ### Upload Guidelines
        - Ensure transcripts are official and unlocked
        - Verify student name matches records
        - Include all pages of transcript
        """)

        
    

    # Display combined results if available
    if st.session_state.combined_data:
        edited_df = display_combined_results(st.session_state.combined_data)
        
        # Store edited dataframe in session state
        if edited_df is not None:
            st.session_state.combined_data['courses'] = edited_df.to_dict('records')
            
            # Add evaluation button
            if st.button("Evaluate Transfer Credits", key="evaluate_button"):
                with st.spinner("Evaluating transfer credits..."):
                    try:
                        # Create evaluator and process results
                        evaluator = create_evaluator(program_level="undergraduate")
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

if __name__ == "__main__":
    main()