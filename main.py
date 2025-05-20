# main.py
import streamlit as st
from src.gemini_client import GeminiClient
from src.processors import process_multiple_pdfs, combine_transcript_data
from src.display import display_combined_results, display_evaluation_results
from src.evaluator import create_evaluator


st.set_page_config(
    page_title="Transcript Analyzer",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────────
# Helper: Settings UI
# ──────────────────────────────────────────────────────────────────────────

def render_settings(client):
    """Render the Settings tab and persist values in st.session_state."""
    st.header("⚙️ Gemini Settings")
    
    model_ids= client.list_models()    
        # pick a sensible default (session‑state value if it’s still valid, else first)
    default_model = st.session_state.get(
        "model_name", GeminiClient.DEFAULT_MODEL
    )
    default_index = model_ids.index(default_model) if default_model in model_ids else 0
    st.write(default_model)
    selected_model = st.selectbox(
        "Model name",
        options=model_ids,
        index=default_index,
        help="Pick any Gemini model that supports generateContent",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.get("temperature", 0.0),
        step=0.1,
        help="Higher values yield more creative output",
    )

    custom_prompt = st.text_area(
        "Custom extraction prompt (optional)",
        value=st.session_state.get("custom_prompt", ""),
        placeholder="Leave blank to use the built‑in prompt",
        height=160,
    )

    if st.button("Save settings", type="primary"):
        st.session_state.update(
            model_name=selected_model,
            temperature=temperature,
            custom_prompt=custom_prompt,
        )
        st.success("Settings saved!")


# ──────────────────────────────────────────────────────────────────────────
# Upload & Process tab
# ──────────────────────────────────────────────────────────────────────────

def render_upload_tab(client: GeminiClient):
    """Render the Upload & Process tab content."""
    st.header("Upload & Process Transcripts")

    # File upload section
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type="pdf",
            accept_multiple_files=True,
        )
        if uploaded_files:
            st.write(f"{len(uploaded_files)} file(s) uploaded successfully")

            if st.button("Process Transcripts", key="process_button"):
                with st.spinner("Processing transcripts..."):
                    try:
                        # Optionally pass custom prompt if you extend `process_multiple_pdfs`
                        results = process_multiple_pdfs(
                            client,
                            uploaded_files
                        )

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

    with col2:
        st.info(
            """
            ### Upload Guidelines
            - Ensure transcripts are official and unlocked
            - Verify student name matches records
            - Include all pages of transcript
            """
        )

    # Show processed data in subtabs if available
    if st.session_state.get("combined_data"):
        edited_df = display_combined_results(st.session_state.combined_data)
        if edited_df is not None:
            st.session_state.combined_data["courses"] = edited_df.to_dict("records")


# ──────────────────────────────────────────────────────────────────────────
# Review & Evaluate tab
# ──────────────────────────────────────────────────────────────────────────

def render_review_tab(client: GeminiClient):
    """Render the Review & Evaluate tab content."""
    st.header("Evaluate Transfer Credits")

    if not st.session_state.get("combined_data"):
        st.warning("Please upload and process transcripts in the Upload tab first")
        return

    # Evaluation controls
    if st.button("Start Evaluation", key="evaluate_button"):
        with st.spinner("Evaluating transfer credits..."):
            try:
                evaluator = create_evaluator(client)
                evaluation_results = evaluator.evaluate_transcript(
                    st.session_state.combined_data
                )

                # Store evaluation results and set flag
                st.session_state.evaluation_results = evaluation_results
                st.session_state.evaluation_complete = True
            except Exception as e:
                st.error(f"Error during evaluation: {str(e)}")
                st.session_state.evaluation_complete = False

    # Display evaluation results if available
    if (
        st.session_state.evaluation_complete
        and hasattr(st.session_state, "evaluation_results")
    ):
        display_evaluation_results(st.session_state.evaluation_results)


# ──────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────

def main():
    st.title("Transcript Analyzer")

    # ── Session‑state defaults ── #
    if "processed_data" not in st.session_state:
        st.session_state.processed_data = None
    if "combined_data" not in st.session_state:
        st.session_state.combined_data = None
    if "evaluation_complete" not in st.session_state:
        st.session_state.evaluation_complete = False

    # Make sure settings have defaults
    if "model_name" not in st.session_state:
        st.session_state.model_name = GeminiClient.DEFAULT_MODEL
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.0
    if "custom_prompt" not in st.session_state:
        st.session_state.custom_prompt = ""

    # ── Gemini client ── #
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        st.error("Add GOOGLE_API_KEY to your Streamlit secrets!")
        st.stop()

    client = GeminiClient(
        api_key=api_key,
        model_name=st.session_state.model_name,
        temperature=st.session_state.temperature,
    )
    # ── Tabs ── #c
    upload_tab, review_tab, settings_tab = st.tabs(
        [
            "Upload & Process",
            "Review & Evaluate",
            "Settings",
        ]
    )

    with upload_tab:
        render_upload_tab(client)

    with review_tab:
        render_review_tab(client)

    with settings_tab:
        render_settings(client)


if __name__ == "__main__":
    main()
