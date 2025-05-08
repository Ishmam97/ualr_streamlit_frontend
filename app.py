import streamlit as st
import requests
import json
import os

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
                
                st.session_state.chat_history.append({"role": "assistant", "content": result.get("response", "")})
                
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
    for message in st.session_state.chat_history:
        role = "You" if message["role"] == "user" else "UALR Assistant"
        st.markdown(f"**{role}**: {message['content']}")
        st.markdown("---")