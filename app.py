import streamlit as st
import requests
import json
import os
from datetime import datetime

# Get the API URL from environment variable or use default
API_URL = os.environ.get("API_URL","https://ualr-chatbot-backend.onrender.com")

# Page configuration
st.set_page_config(page_title="UALR Chatbot Demo", layout="centered")
st.title("🎓 UALR Q&A Chatbot")

# Sidebar for API key input
st.sidebar.title("⚙️ Options")
api_key = st.sidebar.text_input(
    "Google Gemini API Key", 
    type="password", 
    placeholder="Enter your API key...", 
    key="api_key_input"
)

# Model selection
model = st.sidebar.selectbox(
    "Model",
    ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"],
    index=0
)

# Number of documents to retrieve
# k = st.sidebar.slider("Number of documents to retrieve", 1, 10, 3)

k=5

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

# Main input for query
query = st.text_input(
    "Ask a question about UALR:", 
    placeholder="Type your question here...", 
    key="query_input"
)

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "feedback_log" not in st.session_state:
    st.session_state.feedback_log = []

# Submit button
if st.button("Submit", key="submit_button"):
    if query and api_key:
        with st.spinner("Fetching response..."):
            try:
                payload = {
                    "query": query,
                    "api_key": api_key,
                    "k": k,
                    "model": model
                }
                
                st.session_state.chat_history.append({"role": "user", "content": query})
                
                response = requests.post(f"{API_URL}/query", json=payload, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                
                st.session_state.chat_history.append({"role": "assistant",
                "content": result.get("response", ""),
                "query": query,
                "retrieved_docs": result.get("retrieved_docs", [])
                })
                
                with st.expander("🔍 Retrieved Information"):
                    if result.get("retrieved_docs"):
                        for i, doc in enumerate(result["retrieved_docs"], 1):
                            st.markdown(f"**Document {i}**")
                            st.write(doc.get("content", "No content available"))
                    else:
                        st.warning("No relevant documents were retrieved.")
                
                st.markdown("### Answer")
                st.write(result.get("response", "No response returned."))
                
            except requests.exceptions.HTTPError as e:
                error_msg = "Unknown error"
                try:
                    error_msg = e.response.json().get('detail', 'Unknown error')
                except:
                    error_msg = str(e)
                st.error(f"Backend error: {error_msg}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to backend: {e}")
            except (json.JSONDecodeError, KeyError) as e:
                st.error(f"Received an invalid response from the backend: {e}")
    else:
        st.warning("Please provide both a question and a valid API key.")

# Display chat history
if st.session_state.chat_history:
    st.markdown("### Chat History")
    for i, message in enumerate(st.session_state.chat_history):
        role = "You" if message["role"] == "user" else "UALR Assistant"
        st.markdown(f"**{role}**: {message['content']}")

        if message["role"] == "assistant":
            feedback_key_base = f"feedback_{i}" # Unique key for each message
            
            # Check if feedback already given for this message
            feedback_given = any(
                item.get("query") == message.get("query") and item.get("response") == message.get("content")
                for item in st.session_state.feedback_log
            )

            if not feedback_given:
                cols = st.columns([1, 1, 8]) # Adjust column ratios as needed
                with cols[0]:
                    if st.button("👍", key=f"{feedback_key_base}_up"):
                        feedback_payload = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "query": message.get("query"),
                            "response": message.get("content"),
                            "feedback_type": "thumbs_up",
                            "model_used": model, # From sidebar
                            # "retrieved_docs": message.get("retrieved_docs") # Optionally send docs
                        }
                        try:
                            requests.post(f"{API_URL}/feedback", json=feedback_payload, timeout=10)
                            st.toast("Thanks for your feedback!", icon="✅")
                            st.session_state.feedback_log.append(feedback_payload) # Log locally
                            st.rerun() # To hide buttons after feedback
                        except requests.exceptions.RequestException as e:
                            st.error(f"Failed to submit feedback: {e}")

                with cols[1]:
                    if st.button("👎", key=f"{feedback_key_base}_down"):
                        st.session_state[f"{feedback_key_base}_show_reason"] = True
                        st.rerun()


                if st.session_state.get(f"{feedback_key_base}_show_reason", False):
                    with st.form(key=f"{feedback_key_base}_reason_form"):
                        reason = st.text_area("What was wrong with the response?", key=f"{feedback_key_base}_reason_text")
                        submit_reason = st.form_submit_button("Submit Feedback")

                        if submit_reason:
                            feedback_payload = {
                                "timestamp": datetime.utcnow().isoformat(),
                                "query": message.get("query"),
                                "response": message.get("content"),
                                "feedback_type": "thumbs_down",
                                "thumbs_down_reason": reason,
                                "model_used": model,
                                # "retrieved_docs": message.get("retrieved_docs")
                            }
                            try:
                                requests.post(f"{API_URL}/feedback", json=feedback_payload, timeout=10)
                                st.toast("Thanks for your feedback!", icon="✅")
                                st.session_state.feedback_log.append(feedback_payload)
                                st.session_state[f"{feedback_key_base}_show_reason"] = False # Hide form
                                st.rerun()
                            except requests.exceptions.RequestException as e:
                                st.error(f"Failed to submit feedback: {e}")
            else:
                st.caption("Feedback submitted for this response.")
        st.markdown("---")


# Form for "Chatbot Couldn't Answer"
st.sidebar.markdown("---")
st.sidebar.markdown("### Report an Unanswered Question")
with st.sidebar.form(key="unanswered_question_form"):
    unanswered_query = st.text_input("What question could the chatbot not answer?")
    correct_answer_suggestion = st.text_area("What is the correct answer or what should it have said?")
    submit_suggestion = st.form_submit_button("Submit Suggestion")

    if submit_suggestion:
        if unanswered_query and correct_answer_suggestion:
            feedback_payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "query": unanswered_query, # This is the question the bot FAILED on
                "response": None, # No bot response in this case, or you could put a placeholder
                "feedback_type": "correction_suggestion",
                "corrected_question": unanswered_query, # Or user can refine it
                "correct_answer": correct_answer_suggestion,
                "model_used": model, # The model that was active when user decided to use this form
            }
            try:
                requests.post(f"{API_URL}/feedback", json=feedback_payload, timeout=10)
                st.sidebar.success("Suggestion submitted. Thank you!")
            except requests.exceptions.RequestException as e:
                st.sidebar.error(f"Failed to submit suggestion: {e}")
        else:
            st.sidebar.warning("Please fill in both the question and the suggested answer.")