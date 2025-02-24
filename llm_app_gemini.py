import os
import json
import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime
from telecom_mock_data import SYSTEM_PROMPT, get_relevant_queries, TELECOM_QUERIES

st.title("LLM Chat App with Memory 🧠")
st.caption("Conversational chatbot with personalized memory layer")

# Initialize session state for chat history and session management
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_session" not in st.session_state:
    st.session_state.current_session = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Add conversation context tracking
if "context" not in st.session_state:
    st.session_state.context = {
        "current_topic": None,
        "previous_topics": []
    }

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
        
        # Add conversation context controls
        st.sidebar.title("Conversation Context")
        if st.session_state.context["current_topic"]:
            st.sidebar.info(f"Current topic: {st.session_state.context['current_topic']}")
        
        if st.session_state.context["previous_topics"]:
            selected_topic = st.sidebar.selectbox(
                "Previous Topics",
                st.session_state.context["previous_topics"]
            )
            if st.sidebar.button("Return to Topic"):
                st.chat_message("assistant").markdown(
                    f"Let's return to discussing {selected_topic}. How can I help you with that?"
                )

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

                    # Process user input with context awareness
                    relevant_queries = get_relevant_queries(prompt)
                    
                    # Update context tracking
                    if relevant_queries[0].startswith("SELECT"):
                        new_topic = next(
                            (k for k, v in TELECOM_QUERIES.items() 
                             if any(kw in prompt.lower() for kw in v["keywords"])),
                            None
                        )
                        if new_topic and new_topic != st.session_state.context["current_topic"]:
                            if st.session_state.context["current_topic"]:
                                st.session_state.context["previous_topics"].append(
                                    st.session_state.context["current_topic"]
                                )
                            st.session_state.context["current_topic"] = new_topic
            
                    # Prepare the full prompt with context
                    full_prompt = f"""
{SYSTEM_PROMPT}

Previous conversation:
{conversation_history}

User memories:
{chr(10).join(relevant_memories[-3:] if relevant_memories else [])}

Related SQL Queries:
{chr(10).join(relevant_queries)}

Current message: {prompt}
"""
                    # Update generation config by removing invalid parameter
                    generation_config = {
                        "temperature": 1,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 8192,
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