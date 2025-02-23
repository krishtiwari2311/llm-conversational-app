import os
import json
import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime

st.title("LLM Chat App with Memory 🧠")
st.caption("Conversational chatbot with personalized memory layer")

# Initialize session state for chat history and session management
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_session" not in st.session_state:
    st.session_state.current_session = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Add clear chat function
def clear_chat():
    st.session_state.messages = []

def save_session(user_id, messages, session_id):
    os.makedirs('sessions', exist_ok=True)
    session_file = f'sessions/{user_id}_{session_id}.json'
    with open(session_file, 'w') as f:
        json.dump(messages, f)

def load_session(user_id, session_id):
    try:
        with open(f'sessions/{user_id}_{session_id}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def get_available_sessions(user_id):
    if not os.path.exists('sessions'):
        return []
    sessions = [f.replace(f'{user_id}_', '').replace('.json', '') 
                for f in os.listdir('sessions') 
                if f.startswith(f'{user_id}_')]
    return sorted(sessions, reverse=True)

gemini_api_key = st.text_input("Enter Gemini API Key", type="password")
genai.configure(api_key=gemini_api_key)

# In-memory storage for user prompts and responses
user_memory = {}

if gemini_api_key:
    user_id = st.text_input("Enter your Username")
    
    if user_id:  # Only proceed if user_id is provided
        # Add session management to sidebar
        st.sidebar.title("Chat Controls")
        available_sessions = get_available_sessions(user_id)
        
        if available_sessions:
            selected_session = st.sidebar.selectbox(
                "Select Previous Session",
                ["Current Session"] + available_sessions
            )
            
            if selected_session != "Current Session":
                if st.sidebar.button("Load Selected Session"):
                    st.session_state.messages = load_session(user_id, selected_session)
                    st.session_state.current_session = selected_session
                    st.rerun()

        if st.sidebar.button("Save Current Session"):
            save_session(user_id, st.session_state.messages, st.session_state.current_session)
            st.sidebar.success("Session saved!")

        if st.sidebar.button("Clear Chat History"):
            clear_chat()
            st.session_state.current_session = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Move memory display entirely to sidebar
        # st.sidebar.title("Memory Info")
        # if st.sidebar.button("View My Memory"):
        # if user_id in user_memory:
        #     st.sidebar.write(f"Memory history for **{user_id}**:")
        #     for mem in user_memory[user_id]:
        #         st.sidebar.write(f"- {mem}")
        # else:
        #     st.sidebar.info("No learning history found for this user ID.")

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Chat with Gemini"):
            # Add user message to chat
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner('Thinking...'):
                    # Retrieve relevant memories
                    relevant_memories = user_memory.get(user_id, [])
                    
                    # Create conversation context
                    conversation_history = "\n".join([
                        f"{msg['role']}: {msg['content']}" 
                        for msg in st.session_state.messages[-5:]  # Last 5 messages
                    ])
                    
                    # Prepare the full prompt
                    full_prompt = f"""Previous conversation:
{conversation_history}

User memories:
{chr(10).join(relevant_memories[-3:] if relevant_memories else [])}

Current message: {prompt}
"""
                    # Get response from Gemini API
                    generation_config = {
                    "temperature": 1,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                    "response_mime_type": "text/plain",
                    }
                    model = genai.GenerativeModel(
                            model_name="gemini-1.5-flash-8b",
                            generation_config=generation_config,
                            )
                    response = model.generate_content(full_prompt)

                    if response:
                        answer = response.text
                        st.markdown(answer)  # Changed from st.write to st.markdown
                        st.session_state.messages.append({"role": "assistant", "content": answer})

                        # Store both prompt and response in memory
                        if user_id in user_memory:
                            user_memory[user_id].append(f"Q: {prompt}\nA: {answer}")
                        else:
                            user_memory[user_id] = [f"Q: {prompt}\nA: {answer}"]
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")  # Display the full error for debugging