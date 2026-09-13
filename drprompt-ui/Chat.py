import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime
from api.chat import get_examples, send_chat_message

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="EONE Health", layout="wide")

# =========================================================
#  DATABASE MANAGEMENT (SQLite)
# =========================================================
DB_FILE = "chat_logs.db"

def init_db():
    """Initialize the SQLite database if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create table for logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            username TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            estimated_cost REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_usage(username, prompt, response):
    """
    Calculate tokens and save to DB.
    Note: roughly 4 chars = 1 token. 
    Adjust 'price_per_1k' based on your LLM model (e.g. GPT-4o, GPT-3.5).
    """
    # 1. Estimate Tokens
    input_tokens = len(prompt) // 4
    output_tokens = len(response) // 4
    total_tokens = input_tokens + output_tokens
    
    # 2. Estimate Cost (Example: $0.002 per 1k tokens)
    price_per_1k = 0.002 
    estimated_cost = (total_tokens / 1000) * price_per_1k
    
    # 3. Save to DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO usage_logs (timestamp, username, input_tokens, output_tokens, total_tokens, estimated_cost)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username, input_tokens, output_tokens, total_tokens, estimated_cost))
    conn.commit()
    conn.close()

def get_all_logs():
    """Fetch all logs for the Admin Dashboard."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM usage_logs", conn)
    conn.close()
    
    # Convert timestamp string to datetime object for better charting
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
    return df

# Initialize DB on script load
init_db()

# =========================================================
#  AUTHENTICATION
# =========================================================
def check_password():
    
    def password_entered():
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = st.session_state["username"] 
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["logged_in"] = False
            st.error("😕 User not known or password incorrect")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.title("🔐 EONE Health Login")
        st.markdown("Please log in to access the system.")
        with st.form(key="login_form"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Login", on_click=password_entered)
        return False
    else:
        return True

# =========================================================
#  PAGE: ADMIN DASHBOARD (Reads from DB)
# =========================================================
def show_admin_dashboard():
    st.title("📊 Admin Dashboard")
    
    with st.sidebar:
        st.write(f"Logged in as: **Admin**")
        if st.button("Log out"):
            st.session_state["logged_in"] = False
            del st.session_state["current_user"]
            st.rerun()
    
    # 1. Load Data
    df = get_all_logs()

    if df.empty:
        st.info("No usage data recorded yet. Go chat as 'user1' to generate logs!")
        return

    st.subheader("User Usage Overview")

    # 2. Top Level Metrics
    total_tokens = df["total_tokens"].sum()
    total_cost = df["estimated_cost"].sum()
    active_users = df["username"].nunique()
    total_interactions = len(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tokens", f"{total_tokens:,}")
    col2.metric("Est. Cost", f"${total_cost:.4f}")
    col3.metric("Active Users", active_users)
    col4.metric("Total Interactions", total_interactions)

    st.divider()

    # 3. Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.write("### Usage by User")
        # Group by Username
        user_group = df.groupby("username")["total_tokens"].sum().reset_index()
        st.bar_chart(user_group, x="username", y="total_tokens", color="#3498db")

    with col_chart2:
        st.write("### Daily Traffic")
        # Group by Date
        date_group = df.groupby("date")["total_tokens"].sum().reset_index()
        st.line_chart(date_group, x="date", y="total_tokens", color="#e74c3c")

    # 4. Raw Data Table
    st.write("### Detailed Logs")
    st.dataframe(
        df[["timestamp", "username", "input_tokens", "output_tokens", "total_tokens", "estimated_cost"]].sort_values("timestamp", ascending=False),
        width="stretch"
    )

# =========================================================
#  PAGE: CHAT INTERFACE (Writes to DB)
# =========================================================
def show_chat_interface():
    st.title("EONE Health Demo")
    
    # --- Sidebar ---
    with st.sidebar:
        current_user = st.session_state.get("current_user", "User")
        st.write(f"Logged in as: **{current_user}**")
        if st.button("Log out"):
            st.session_state["logged_in"] = False
            del st.session_state["current_user"]
            st.rerun()
        st.divider()
        
        # Language & Examples
        st.header("Example Questions")
        language = st.selectbox("Choose your language", ["ko", "en"], index=1 if os.getenv("ENV") == "local" else 0)
        
        examples = get_examples(language)
        question_options = []
        if examples and "categories" in examples:
            categories = examples["categories"]
            for key in categories.keys():
                question_options.extend(categories[key]["questions"])
        else:
            question_options = ["No examples available"]

        if question_options and question_options[0] != "No examples available":
            selected_question = st.selectbox("Choose your example question", question_options, index=0)
        else:
            selected_question = None

    # --- Chat State ---
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [
            {"role": "assistant",
             "content": "안녕하세요! 저는 이원헬스 도우미 챗봇입니다. 궁금한 내용을 질문해 보세요. Hello! I'm the Ewon Health Assistant chatbot."}
        ]

    # --- Display Messages ---
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state['messages']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # --- Input Area ---
    input_container = st.container()
    with input_container:
        if selected_question:
            st.info(f"**📝 {selected_question}**")
            col1, col2 = st.columns([1, 6])
            with col1:
                if st.button("🚀 Ask it.", type="primary", key="ask_button"):
                    prompt = selected_question
                else:
                    prompt = None
            with col2:
                if st.button("❌ Cancel", key="cancel_button"):
                    if 'random_example_index' in st.session_state:
                        del st.session_state.random_example_index
                    st.rerun()
        else:
            prompt = None

        if not prompt:
            prompt = st.chat_input(placeholder="Your question....")

    # --- Handle Processing ---
    if prompt:
        # Show User Message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        st.session_state['messages'].append({"role": "user", "content": prompt})

        # Generate Response
        with chat_container:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # --- ANIMATION RESTORED HERE ---
                loading_html = """
                <div style="display: flex; align-items: center;">
                    <style>
                        .pulse-ring { width: 20px; height: 20px; margin-right: 10px; background-color: #3498db; border-radius: 50%; animation: pulse-ring 1.25s cubic-bezier(0.215, 0.61, 0.355, 1) infinite; }
                        @keyframes pulse-ring { 0% { transform: scale(0.33); opacity: 1; } 80%, 100% { transform: scale(1); opacity: 0; } }
                    </style>
                    <div class="pulse-ring"></div>
                    <span style="font-style: italic; color: #555;">Extracting from Database...</span>
                </div>
                """
                message_placeholder.markdown(loading_html, unsafe_allow_html=True)
                # -------------------------------

                try:
                    # Stream response
                    response_generator = send_chat_message(
                        messages=st.session_state['messages'],
                        stream=True
                    )
                    for chunk in response_generator:
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    bot_reply = full_response
                    
                    # ---------------------------------------------------------
                    # !!! CRITICAL: SAVE USAGE TO DB HERE !!!
                    # ---------------------------------------------------------
                    log_usage(
                        username=current_user,
                        prompt=prompt,
                        response=bot_reply
                    )
                    # ---------------------------------------------------------

                except Exception as e:
                    bot_reply = f"Error: {e}"
                    message_placeholder.markdown(bot_reply)

        st.session_state['messages'].append({"role": "assistant", "content": bot_reply})
        
        # Cleanup
        if 'random_example_index' in st.session_state:
            del st.session_state.random_example_index

    # Auto Scroll Script
    st.markdown("""
    <script>
    function scrollToBottom() {
        const chatMessages = document.querySelectorAll('div[data-testid="stChatMessage"]');
        if (chatMessages.length > 0) {
            chatMessages[chatMessages.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }
    setTimeout(scrollToBottom, 500);
    </script>
    """, unsafe_allow_html=True)


# =========================================================
#  MAIN ROUTER
# =========================================================

if not check_password():
    st.stop()

current_user = st.session_state.get("current_user", "")

if current_user == "admin":
    show_admin_dashboard()
else:
    show_chat_interface()