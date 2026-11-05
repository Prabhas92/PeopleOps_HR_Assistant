# =========================================================
# PEOPLEOPS HR ASSISTANT
# Streamlit Frontend (Enhanced UI for Databricks)
# =========================================================

# ---------------------------------------------------------
# 1. IMPORTS
# ---------------------------------------------------------

import streamlit as st
from peopleops_agent import ask_peopleops


# ---------------------------------------------------------
# 2. PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="PeopleOps HR Assistant",
    page_icon="👥",
    layout="centered",
    initial_sidebar_state="expanded"
)


# ---------------------------------------------------------
# 3. CUSTOM CSS STYLING
# ---------------------------------------------------------

st.markdown(
    """
    <style>
    /* Main container styling */
    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Header styling */
    .app-title-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.2rem;
    }
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #FF3621 0%, #FF6B4A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .app-subtitle {
        color: #6c757d;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    /* Welcome Card */
    .welcome-card {
        padding: 24px;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(255, 54, 33, 0.04) 0%, rgba(13, 202, 240, 0.04) 100%);
        border: 1px solid rgba(128, 128, 128, 0.15);
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
    }
    .welcome-card h3 {
        margin-top: 0;
        color: #1f2937;
    }

    /* Suggestion Buttons layout helper */
    .suggestion-header {
        font-weight: 600;
        color: #4b5563;
        margin-bottom: 0.75rem;
        font-size: 0.95rem;
    }

    /* Sidebar polish */
    .sidebar-user-badge {
        background-color: rgba(255, 54, 33, 0.08);
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #d9381e;
        font-weight: 600;
        margin-bottom: 1rem;
        border-left: 3px solid #FF3621;
    }

    /* Custom scrollbar & chat enhancements */
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# 4. SESSION STATE INITIALIZATION
# ---------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# 5. SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("### 👥 PeopleOps")
    st.caption("Enterprise HR Intelligent Assistant")
    
    st.markdown(
        '<div class="sidebar-user-badge">🟢 Connected via Databricks</div>', 
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("📌 Capabilities")
    st.markdown(
        """
        - 👤 **Employee Details**: View profile & info
        - 📊 **Leave Balances**: Check earned & sick leaves
        - 📚 **HR Policies**: RAG-powered document search
        - 🎫 **Auto-Ticketing**: Creates a support ticket if unresolved
        """
    )

    st.divider()

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.caption("Powered by Databricks Mosaic AI & Vector Search")


# ---------------------------------------------------------
# 6. APPLICATION HEADER
# ---------------------------------------------------------

st.markdown(
    """
    <div class="app-title-container">
        <span style="font-size: 2.2rem;">👥</span>
        <div class="app-title">PeopleOps HR Assistant</div>
    </div>
    <div class="app-subtitle">
        Your intelligent workplace companion for instant HR answers, leave balances, and seamless support tickets.
    </div>
    """,
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# 7. WELCOME MESSAGE & SUGGESTED PROMPTS
# ---------------------------------------------------------

if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome-card">
            <h3>👋 Welcome to PeopleOps!</h3>
            <p style="color: #4b5563; margin-bottom: 0;">
                I'm connected to your employee records and company policy knowledge base. 
                Ask me about your leave balances, benefits, company guidelines, or request HR assistance anytime.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="suggestion-header">💡 Quick Suggested Questions:</div>', unsafe_allow_html=True)

    suggestions = [
        "Show my employee details",
        "What is my current leave balance?",
        "Can earned leave be carried forward?",
        "What happens to unused leave when I resign?"
    ]

    # Create a nice 2x2 grid for suggested questions
    col1, col2 = st.columns(2)
    for idx, suggestion in enumerate(suggestions):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            if st.button(suggestion, use_container_width=True, key=f"sugg_{idx}"):
                st.session_state.selected_question = suggestion
                st.rerun()


# ---------------------------------------------------------
# 8. DISPLAY CHAT HISTORY
# ---------------------------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------------------------------------------------
# 9. CHAT INPUT & HANDLERS
# ---------------------------------------------------------

prompt = st.chat_input("Ask your HR question (e.g., 'Check my sick leave balance')...")

# Handle quick suggestion button clicks
if "selected_question" in st.session_state:
    prompt = st.session_state.pop("selected_question")



# ---------------------------------------------------------
# 10. PROCESS EMPLOYEE QUESTION
# ---------------------------------------------------------

if prompt:

    # Preserve previous conversation messages
    conversation_history = st.session_state.messages.copy()

    # Display employee question
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):

        with st.spinner("PeopleOps Assistant is thinking..."):

            try:

                answer = ask_peopleops(
                    question=prompt,
                    conversation_history=conversation_history
                )

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:

                error_message = (
                    "Sorry, I couldn't process your request "
                    "at the moment. Please try again."
                )

                st.error(error_message)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })

                print(
                    f"PeopleOps application error: {error}"
                )
