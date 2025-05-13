import streamlit as st
import requests
import json
import os
from datetime import datetime
from streamlit_feedback import streamlit_feedback # Import the component

# Get the API URL from environment variable or use default
API_URL = os.environ.get("API_URL", "http://backend:8000")

# Page configuration
st.set_page_config(page_title="UALR Chatbot Demo", layout="centered")
st.title("🎓 UALR Q&A Chatbot")

st.sidebar.title("⚙️ Options")
api_key = st.sidebar.text_input(
    "Google Gemini API Key",
    type="password",
    placeholder="Enter your API key...",
    key="api_key_input" # The value will be in st.session_state.api_key_input if needed elsewhere
)

# Model selection
model = st.sidebar.selectbox(
    "Model",
    ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"],
    index=0
)

# Number of documents to retrieve
k = 5

# Display API connection info
with st.sidebar.expander("Connection Info"):
    st.write(f"API URL: {API_URL}")
    if st.button("Test Connection"):
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Connected to backend API")
            else:
                st.error(f"❌ API returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Failed to connect: {e}")

# Sidebar form for reporting unanswered questions
st.sidebar.markdown("---")
st.sidebar.markdown("### Report an Unanswered Question")
with st.sidebar.form(key="unanswered_question_form"):
    unanswered_query = st.text_input("What question could the chatbot not answer?")
    correct_answer_suggestion = st.text_area("What is the correct answer or what should it have said?")
    submit_suggestion = st.form_submit_button("Submit Suggestion")
    if submit_suggestion:
        if submit_suggestion:
            if unanswered_query and correct_answer_suggestion:
                feedback_payload = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query": unanswered_query,
                    "response": None,  # No specific chatbot response is being rated here
                    "feedback_type": "correction_suggestion",
                    "corrected_question": unanswered_query,
                    "correct_answer": correct_answer_suggestion,
                    "model_used": model,  # Current model selection from sidebar
                }
                try:
                    print(f"Submitting correction suggestion: {feedback_payload}")
                    response = requests.post(f"{API_URL}/feedback", json=feedback_payload, timeout=10)
                    response.raise_for_status()  # Check for HTTP errors
                    st.sidebar.success("Suggestion submitted. Thank you!")
                except requests.exceptions.RequestException as e:
                    st.sidebar.error(f"Failed to submit suggestion: {e}")
            else:
                st.sidebar.warning("Please fill in both the question and the suggested answer.")

# Initialize session state for messages and feedback tracking
if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback_states" not in st.session_state:
    st.session_state.feedback_states = {} # To store feedback status for each message_id

# Display chat messages from history
for i, msg_data in enumerate(st.session_state.messages):
    with st.chat_message(msg_data["role"]):
        st.markdown(msg_data["content"])
        if msg_data["role"] == "assistant":
            # Ensure message_id exists (for robustness, e.g. if migrating old messages)
            if "message_id" not in msg_data:
                 # Create a fallback message_id if missing
                msg_data["message_id"] = f"asst_fallback_{i}_{datetime.utcnow().timestamp()}"

            feedback_key = f"feedback_{msg_data['message_id']}"

            # Initialize feedback_states dictionary if it doesn't exist
            if "feedback_states" not in st.session_state:
                st.session_state.feedback_states = {}

            # Check if feedback has already been given for this message
            if feedback_key in st.session_state.feedback_states:
                # Display submitted feedback
                try:
                    score_display = st.session_state.feedback_states[feedback_key]
                    st.markdown(f"<small>Feedback: {score_display} (submitted)</small>", unsafe_allow_html=True)
                except KeyError:
                    # Handle case where the key might be missing despite the check
                    st.markdown("<small>Feedback status unavailable</small>", unsafe_allow_html=True)
                    # Recreate the feedback key entry (optional)
                    st.session_state.feedback_states[feedback_key] = "⚠️"
            else:
                # Show the feedback widget if no feedback has been given yet
                feedback = streamlit_feedback(
                    feedback_type="thumbs",
                    optional_text_label="[Optional] Explain your feedback",
                    key=feedback_key,
                )
                if feedback:
                    # Store feedback to prevent re-submission and to update UI
                    st.session_state.feedback_states[feedback_key] = feedback["score"]

                    # Determine feedback type and reason field based on thumbs direction
                    if feedback["score"] == "👍":
                        feedback_type_val = "thumbs_up"
                        reason_field = "thumbs_up_reason"
                    else:
                        feedback_type_val = "thumbs_down"
                        reason_field = "thumbs_down_reason"

                    # Create feedback payload with the correct field structure
                    feedback_payload = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "query": msg_data.get("query", "Unknown query (feedback)"),
                        "response": msg_data["content"],
                        "feedback_type": feedback_type_val,
                        reason_field: feedback.get("text"),  # Use the appropriate reason field
                        "model_used": msg_data.get("model_used", "Unknown model (feedback)"),
                        "source_message_id": msg_data["message_id"],
                        # "retrieved_docs": msg_data.get("retrieved_docs")
                    }
                    print(f"Submitting feedback payload: {feedback_payload}")

                    try:
                        api_response = requests.post(f"{API_URL}/feedback", json=feedback_payload, timeout=10)
                        api_response.raise_for_status()
                        st.toast(f"Feedback ({feedback['score']}) submitted. Thank you!", icon="✅")
                        st.rerun()  # Rerun to update UI and show "Feedback given"
                    except requests.exceptions.HTTPError as http_err:
                        st.error(f"API error submitting feedback: {http_err}")
                        # Remove the feedback state to allow retry
                        if feedback_key in st.session_state.feedback_states:
                            del st.session_state.feedback_states[feedback_key]
                    except requests.exceptions.RequestException as req_err:
                        st.error(f"Connection error submitting feedback: {req_err}")
                        if feedback_key in st.session_state.feedback_states:
                            del st.session_state.feedback_states[feedback_key]

# Chat input for user queries
if prompt := st.chat_input("Ask a question about UALR:"):
    if not api_key: # api_key is the direct value from st.sidebar.text_input
        st.error("Please provide a valid API key in the sidebar.")
    else:
        # Add user message to chat history with a unique ID
        user_message_timestamp = datetime.utcnow().isoformat()
        user_msg_id = f"user_{user_message_timestamp}_{len(st.session_state.messages)}"
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "message_id": user_msg_id
        })
        # User message will be displayed on the next rerun by the loop above

        # Display assistant response
        # No need for `with st.chat_message("assistant")` here as the loop handles it
        with st.spinner("Thinking..."):
            try:
                payload = {
                    "query": prompt,
                    "api_key": api_key,
                    "k": k,
                    "model": model # Current model selection for this query
                }
                response = requests.post(f"{API_URL}/query", json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()

                assistant_response_content = result.get("response", "Sorry, I could not generate a response.")
                retrieved_docs = result.get("retrieved_docs", [])

                # Add assistant message to chat history with relevant data
                assistant_message_timestamp = datetime.utcnow().isoformat()
                assistant_msg_id = f"asst_{assistant_message_timestamp}_{len(st.session_state.messages)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response_content,
                    "query": prompt,  # Store the user query that led to this response
                    "retrieved_docs": retrieved_docs,
                    "model_used": model,  # Store the model used for this specific response
                    "message_id": assistant_msg_id
                })
                st.rerun()

            except requests.exceptions.HTTPError as e:
                error_msg = "Unknown error"
                try:
                    error_detail = e.response.json().get('detail', str(e.response.text))
                    error_msg = f"{e.response.status_code}: {error_detail}"
                except json.JSONDecodeError:
                    error_msg = f"{e.response.status_code}: {e.response.text}"
                except AttributeError: # If e.response is None or not as expected
                    error_msg = str(e)
                st.error(f"Backend error: {error_msg}")
                # Optionally, add an error message to the chat display itself
                # assistant_error_msg_id = f"asst_error_{datetime.utcnow().isoformat()}_{len(st.session_state.messages)}"
                # st.session_state.messages.append({
                #     "role": "assistant", "content": f"Error from backend: {error_msg}",
                #     "query": prompt, "model_used": model, "message_id": assistant_error_msg_id, "is_error": True
                # })
                # st.experimental_rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to backend: {e}")
            except (json.JSONDecodeError, KeyError) as e:
                st.error(f"Received an invalid response from the backend: {e}")
