import os
import sys
import uuid
import json
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# ==========================================
# 1. IMMEDIATE PATH & ENVIRONMENT RESOLUTION
# ==========================================
script_dir = Path(__file__).resolve().parent  # points to src/
project_root = script_dir.parent              # climbs to project root

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

# Import the compiled graph and tools list dynamically
from src.agent import fde_agent, driver_agent, load_system_prompt , content_to_text
from src.voice import GnaniVoiceClient, GnaniVoiceError, SUPPORTED_LANGUAGES
from src.voice.brief import split_voice_brief, fallback_brief
from src.voice.driver_alerts import build_driver_alert, ALERT_LANGUAGES

# ==========================================
# 2. SQL CREDENTIALS MAPPING FROM .ENV
# ==========================================
db_host = os.getenv("SQL_SERVER_HOST", "localhost")
db_port = os.getenv("SQL_SERVER_PORT", "1433")
db_user = os.getenv("SQL_AGENT_USER", "USR_FDE_RO")
db_password = os.getenv("SQL_AGENT_PASSWORD")

# Engine for the Agent to write logs using its standard credentials
connection_string = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={db_host},{db_port};"
    f"DATABASE=master;"
    f"UID={db_user};"
    f"PWD={db_password};"
    f"Encrypt=no;"
    f"TrustServerCertificate=yes;"
)

log_params = urllib.parse.quote_plus(connection_string)

log_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={log_params}")

def write_audit_log(session_id, node_name, tool_name, content):
    """Silently writes agent execution traces to the SQL audit table using agent permissions."""
    try:
        with log_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO FDE_VIEWS.AgentAuditLog (SessionID, NodeExecuted, ToolName, Content)
                VALUES (:session_id, :node_name, :tool_name, :content)
            """), {
                "session_id": session_id,
                "node_name": node_name,
                "tool_name": tool_name,
                "content": content
            })
            conn.commit()
    except Exception as e:
        print(f"Audit Log Failed (Silent): {e}")

# ==========================================
# 3. PAGE CONFIGURATION & ENTERPRISE THEME
# ==========================================
st.set_page_config(
    page_title="FDE Supply Chain Dispatch Console",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #E2E8F0; }
    div[data-testid="stSidebar"] { background-color: #111622; border-right: 1px solid #1E293B; }
    .stMarkdown code { background-color: #1E293B !important; color: #38BDF8 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. ROLE-SPECIFIC SESSION & THREAD MANAGEMENT
# ==========================================
# Each role gets its own LangGraph thread and chat history.
if "role_sessions" not in st.session_state:
    st.session_state.role_sessions = {}


@st.cache_resource(show_spinner=False)
def get_voice_client() -> GnaniVoiceClient:
    return GnaniVoiceClient()

voice = get_voice_client()

# ==========================================
# 5. ROLE SELECTION & SHARED SETTINGS
# ==========================================
with st.sidebar:
    st.image(str(script_dir / "image_L25X5q.png") if (script_dir / "image_L25X5q.png").exists() else "https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=65)
    st.title("ThermaBrain")
    selected_view = st.radio(
        "Choose your workspace",
        ["Fleet / Logistics Manager", "Truck Driver", "Security & Audit Logs"],
        key="selected_view",
    )
    app_mode = "🛡️ Security & Audit Logs" if selected_view == "Security & Audit Logs" else "🧊 Dispatch Console"
    role = "driver" if selected_view == "Truck Driver" else "manager"
    role_key = role

    st.markdown("---")
    st.markdown("**🎙️ Gnani Voice**")
    if voice.configured:
        st.caption(f"STT `{voice.stt_model}` · TTS `{voice.tts_model}`")
    else:
        st.warning("Set `GNANI_API_KEY` in `.env` to enable voice.", icon="🔑")
    lang_options = {"indic-auto": "Auto-detect language", **SUPPORTED_LANGUAGES}
    speak_lang = st.selectbox("Speaking language", list(lang_options), format_func=lang_options.get, key="speak_lang")
    speak_replies = st.toggle("🔊 Speak the reply", value=True, key="speak_replies", disabled=not voice.configured)

    if app_mode == "🧊 Dispatch Console":
        session = st.session_state.role_sessions.setdefault(role_key, {})
        session.setdefault("thread_id", str(uuid.uuid4()))
        session.setdefault("ui_messages", [])
        session.setdefault("primed", False)
        session.setdefault("last_audio_key", None)
        thread_id = session["thread_id"]
        ui_messages = session["ui_messages"]
        thread_config = {"configurable": {"thread_id": thread_id}}
        st.markdown("---")
        st.caption(f"{selected_view} session: `{thread_id[:8]}...`")
        if st.button("🗑️ Clear this chat", use_container_width=True):
            session.update({"thread_id": str(uuid.uuid4()), "ui_messages": [], "primed": False, "last_audio_key": None})
            st.rerun()

    st.markdown("---")
    st.caption(f"Reasoning model: `{os.getenv('Agent_llm', 'DEEPSEEK')}`")

# ==========================================
# 6. VIEW ROUTING (DISPATCH VS AUDIT)
# ==========================================

if app_mode == "🧊 Dispatch Console":
    # ------------------------------------------
    # TAB 1: CHAT UI & AGENT EXECUTION
    # ------------------------------------------
    if role == "manager":
        st.title("Fleet Operations Intelligence")
        st.caption("Investigate fleet-wide cold-chain risks, telemetry, route disruptions and SOP compliance.")
    else:
        st.title("Driver Assist")
        st.caption("Report a problem, ask what to do next, or speak in your preferred language.")
        st.info("The driver assistant can look up only the vehicle ID entered here. Stop safely before using the app.", icon="🚚")
        driver_vehicle_id = st.text_input("Your vehicle ID", key="driver_vehicle_id", placeholder="e.g. TRK-1042")

    for entry in ui_messages:
        with st.chat_message(entry["role"], avatar="👤" if entry["role"] == "user" else "🤖"):
            if role == "manager" and "traces" in entry:
                for trace in entry["traces"]:
                    if trace["type"] == "tool_input":
                        st.markdown(f"**⚡ Intent Recognized:** `{trace['name']}`")
                        with st.expander(f"📥 View Generated Input ({trace['name']})", expanded=False):
                            st.json(trace["args"])
                    elif trace["type"] == "tool_output":
                        with st.expander(f"📤 View Raw Output ({trace['name']})", expanded=False):
                            st.code(trace["content"], language="text")
            st.markdown(entry["content"])
            if entry.get("audio"):
                st.audio(entry["audio"], format="audio/wav")

    # ---- Voice input (Gnani Prisma STT) -------------------------------------------------
    voice_text, voice_lang = "", None
    with st.expander("🎙️ Speak to the assistant", expanded=(role == "driver")):
        recording = st.audio_input("Record your question", key=f"mic_{role}")
        if recording is not None:
            audio_bytes = recording.getvalue()
            audio_key = hash(audio_bytes)
            if audio_key != session["last_audio_key"]:       # don't re-run on every Streamlit rerun
                session["last_audio_key"] = audio_key
                if not voice.configured:
                    st.error("Voice needs GNANI_API_KEY in your .env file.")
                else:
                    try:
                        with st.spinner("Transcribing with Gnani Prisma..."):
                            result = voice.transcribe(
                                audio_bytes,
                                language_code=st.session_state.speak_lang,
                                keyterms=["reefer", "cold chain", "SOP", "telemetry", "breach", "vaccine", "dispatch"],
                            )
                        if result.text:
                            voice_text, voice_lang = result.text, result.language_code
                        else:
                            st.warning("I couldn't hear any speech. Please try again closer to the mic.")
                    except GnaniVoiceError as err:
                        st.error(f"🎙️ {err}")

    typed_input = st.chat_input("Ask about your shipment, temperature, or next action..." if role == "driver" else "Ask about fleet telemetry, incidents, routes, or compliance...")
    user_input = typed_input or voice_text
    if role == "driver" and user_input:
        if not st.session_state.get("driver_vehicle_id", "").strip():
            st.warning("Enter your vehicle ID before sending a question.")
            user_input = ""
        else:
            user_input = f"My vehicle ID is {st.session_state.driver_vehicle_id.strip()}. Driver question: {user_input}"
    reply_lang = voice_lang if voice_text else None

    if user_input:

        shown = f"🎙️ _({SUPPORTED_LANGUAGES.get(voice_lang, voice_lang)})_ {user_input}" if voice_text else user_input
        ui_messages.append({"role": "user", "content": shown})
        with st.chat_message("user", avatar="👤"):
            st.markdown(shown)

        with st.chat_message("assistant", avatar="🧊" if role == "manager" else "🚚"):
            final_response = ""
            current_traces = [] 
            
            with st.status("Checking your request..." if role == "driver" else "🧠 Initializing Core Reasoner Node...", expanded=(role == "manager")) as status:
                payload_msgs = [HumanMessage(content=user_input)]
                if not session["primed"]:   # the dispatcher prompt was previously never sent from the UI
                    payload_msgs.insert(0, SystemMessage(content=load_system_prompt(role)))
                    session["primed"] = True
                active_agent = driver_agent if role == "driver" else fde_agent
                events = active_agent.stream(
                    {"messages": payload_msgs}, 
                    config=thread_config,
                    stream_mode="updates"
                )
                
                for event in events:
                    for node_name, node_state in event.items():
                        
                        if node_name == "reasoner":
                            latest_msg = node_state["messages"][-1]
                            
                            # A. Intercept Tool Call Requests (Inputs)
                            if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                                status.update(label="Checking operational data..." if role == "driver" else "🧠 Agent generated tool parameters...")
                                for tool_call in latest_msg.tool_calls:
                                    if role == "manager":
                                        st.markdown(f"**⚡ Intent Recognized:** `{tool_call['name']}`")
                                        with st.expander(f"📥 View Generated Input ({tool_call['name']})", expanded=False):
                                            st.json(tool_call['args'])
                                    
                                    current_traces.append({
                                        "type": "tool_input",
                                        "name": tool_call['name'],
                                        "args": tool_call['args']
                                    })
                                    
                                    write_audit_log(
                                        session_id=thread_id,
                                        node_name="reasoner",
                                        tool_name=tool_call['name'],
                                        content=json.dumps(tool_call['args'])
                                    )
                            
                            # B. Intercept Final Generation
                            if latest_msg.content:
                                final_response = content_to_text(latest_msg.content)
                                status.update(label="Preparing your instructions..." if role == "driver" else "📝 Generating Operational Resolution Report...")
                                
                                write_audit_log(
                                    session_id=thread_id,
                                    node_name="reasoner_final",
                                    tool_name="LLM Text Synthesis",
                                    content=final_response
                                )
                                
                        elif node_name == "tools":
                            status.update(label="Retrieving trip and safety information..." if role == "driver" else "🔧 Executing Enterprise Subsystem Tools...")
                            for msg in node_state.get("messages", []):
                                if isinstance(msg, ToolMessage):
                                    if role == "manager":
                                        with st.expander(f"📤 View Raw Output ({msg.name})", expanded=False):
                                            st.code(msg.content, language="text")
                                        
                                    current_traces.append({
                                        "type": "tool_output",
                                        "name": msg.name,
                                        "content": msg.content
                                    })
                                    
                                    write_audit_log(
                                        session_id=thread_id,
                                        node_name="tools",
                                        tool_name=msg.name,
                                        content=msg.content
                                    )
                
                status.update(label="Ready" if role == "driver" else "Incident Matrix Evaluation Complete", state="complete", expanded=False)
                
            if final_response:
                visible, brief = split_voice_brief(final_response)
                st.markdown(visible)
                if role == "driver":
                    st.caption("If there is an immediate safety risk, stop safely and contact your dispatcher. Do not use the chatbot while driving.")
                reply_audio = None
                if st.session_state.speak_replies and voice.configured:
                    try:
                        spoken = brief or fallback_brief(visible)
                        tts_lang = reply_lang if reply_lang in SUPPORTED_LANGUAGES else (
                            st.session_state.speak_lang if st.session_state.speak_lang in SUPPORTED_LANGUAGES else "auto")
                        with st.spinner("Synthesizing speech with Gnani Timbre..."):
                            reply_audio = voice.synthesize(spoken, language=tts_lang)
                        st.audio(reply_audio, format="audio/wav", autoplay=bool(voice_text))
                    except GnaniVoiceError as err:
                        st.caption(f"🔇 Voice reply unavailable: {err}")
                ui_messages.append({
                    "role": "assistant",
                    "content": visible,
                    "traces": current_traces,
                    "audio": reply_audio,
                })
            else:
                error_fallback = "⚠️ Execution Timeout: System engine encountered an unresolved processing edge case."
                st.error(error_fallback)


elif app_mode == "🛡️ Security & Audit Logs":
    # ------------------------------------------
    # TAB 3: AUDIT LOG VIEWER (REQUIRES ADMIN CREDENTIALS FROM .ENV OR INPUT)
    # ------------------------------------------
    st.title("🛡️ Enterprise Agent Audit Trail")
    st.caption("Secure database inspection of FDE_VIEWS.AgentAuditLog")
    
    st.markdown("### Database Authorization Gate")
    st.markdown("Enter high-privilege administrative credentials (defined in `.env` as `SQL_ADMIN_USER`) to query audit logs.")
    
    with st.form("admin_auth_form"):
        col1, col2 = st.columns(2)
        with col1:
            input_user = st.text_input("Admin Username", value=os.getenv("SQL_ADMIN_USER", ""))
        with col2:
            input_pass = st.text_input("Admin Password", type="password", value="")
            
        submit_admin = st.form_submit_button("Authenticate & Load Logs", use_container_width=True)

    if submit_admin:
        expected_admin_user = os.getenv("SQL_ADMIN_USER")
        expected_admin_pass = os.getenv("SQL_ADMIN_PASSWORD")
        
        if input_user == expected_admin_user and input_pass == expected_admin_pass:
            try:
                # Build an isolated admin connection string for viewing data
                admin_params = urllib.parse.quote_plus(
                    "DRIVER={ODBC Driver 18 for SQL Server};"
                    f"SERVER={db_host},{db_port};"
                    "DATABASE=master;"
                    f"UID={input_user};"
                    f"PWD={input_pass};"
                    "Encrypt=no;"
                    "TrustServerCertificate=yes;"
                )
                admin_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={admin_params}")
                
                with admin_engine.connect() as conn:
                    query = """
                        SELECT LogID, Timestamp, SessionID, NodeExecuted, ToolName, Content 
                        FROM FDE_VIEWS.AgentAuditLog 
                        ORDER BY Timestamp DESC
                    """
                    df = pd.read_sql(query, conn)
                
                st.success("✅ Authenticated successfully as Admin.")
                
                if not df.empty:
                    st.dataframe(
                        df,
                        column_config={
                            "LogID": st.column_config.NumberColumn("ID", format="%d"),
                            "Timestamp": st.column_config.DatetimeColumn("Execution Time", format="DD/MM/YYYY-h:mm a"),
                            "SessionID": "Session Token",
                            "NodeExecuted": "Graph Node",
                            "ToolName": "Tool Triggered",
                            "Content": "Raw Payload Data"
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=600
                    )
                else:
                    st.info("No audit logs found in the database. Run a query in the Dispatch Console first.")
                    
            except Exception as e:
                st.error(f"Database Query Failed: {e}")
        else:
            st.error("❌ Invalid Administrator Credentials.")