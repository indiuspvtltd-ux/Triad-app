import streamlit as st
import streamlit.components.v1 as components
import os
import io
import sqlite3
import hashlib
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

st.set_page_config(page_title="The Triad Vault System", layout="centered")

# ==========================================
# DATABASE SETUP (Users & Invite Keys)
# ==========================================
def init_db():
    conn = sqlite3.connect('vault_users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, 
                    password TEXT, 
                    folder_id TEXT, 
                    is_admin INTEGER
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS invite_codes (
                    code TEXT PRIMARY KEY, 
                    is_used INTEGER
                )''')
    conn.commit()
    
    # Create default master admin if none exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", ('admin', hashed_pw, '1UwuA56of_7fc4WkpuUqqSZSAKsgHqEoE', 1))
        conn.commit()
    conn.close()

init_db()

# ==========================================
# CUSTOM CSS: Modern Techy Glossy & Squared UI
# ==========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #09071b, #1a163b, #111019);
    color: #f0f0f5;
}
.tech-container {
    background: rgba(25, 22, 48, 0.6);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 75, 75, 0.2);
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    margin-bottom: 25px;
}
.glossy-card {
    background: rgba(20, 18, 38, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 22px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
    margin-bottom: 30px;
    transition: transform 0.3s ease, border-color 0.3s ease;
}
.glossy-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255, 75, 75, 0.4);
    box-shadow: 0 12px 40px rgba(255, 75, 75, 0.15);
}
.card-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 15px;
    border-left: 5px solid #ff4b4b;
    padding-left: 12px;
    letter-spacing: 0.5px;
}
[data-baseweb="tab-list"] {
    gap: 15px;
    background-color: transparent;
    padding-bottom: 10px;
}
[data-baseweb="tab"] {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px !important;
    padding: 14px 28px !important;
    color: #a0a0b0 !important;
    font-weight: 700;
    font-size: 1.05rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
[data-baseweb="tab"]:hover {
    background: rgba(255, 75, 75, 0.1);
    border-color: rgba(255, 75, 75, 0.4);
    color: #ffffff !important;
    box-shadow: 0 0 20px rgba(255, 75, 75, 0.2);
}
[aria-selected="true"] {
    background: linear-gradient(135deg, #ff4b4b, #cc2e2e) !important;
    border-color: #ff4b4b !important;
    color: #ffffff !important;
    box-shadow: 0 0 25px rgba(255, 75, 75, 0.5) !important;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ff4b4b, #d92626);
    color: white;
    font-weight: 700;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    transition: all 0.25s ease-in-out;
    box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
}
div.stButton > button[kind="primary"]:hover {
    transform: scale(1.03);
    box-shadow: 0 6px 25px rgba(255, 75, 75, 0.7);
    border-color: #ffffff;
}
.stTextInput > div > div > input, .stFileUploader {
    background-color: rgba(15, 13, 30, 0.8) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# GOOGLE DRIVE OAUTH SETUP (Cloud-Compatible)
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = None

# 1. Check if running on Streamlit Cloud using st.secrets
if "google_token" in st.secrets:
    creds_info = dict(st.secrets["google_token"])
    creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
# 2. Fallback for local testing
elif os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())

drive_service = build('drive', 'v3', credentials=creds)
MASTER_FOLDER_ID = '1UwuA56of_7fc4WkpuUqqSZSAKsgHqEoE'

# ==========================================
# SESSION STATE MANAGEMENT FOR AUTH
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['folder_id'] = ''
    st.session_state['is_admin'] = 0

# ==========================================
# AUTHENTICATION SCREEN (Login / Register)
# ==========================================
if not st.session_state['logged_in']:
    st.markdown('<div class="tech-container">', unsafe_allow_html=True)
    st.title("🔐 The Triad Vault Access")
    st.markdown("##### *Secure Quantum-Encrypted Multi-Tenant Storage Node*")
    st.markdown('</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 IDENTIFY & LOGIN", "📝 PROVISION NEW VAULT"])
    
    with tab1:
        st.markdown('<div class="tech-container">', unsafe_allow_html=True)
        st.subheader("Sign In to Your Node")
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Authenticate Access")
            
            if login_submit:
                conn = sqlite3.connect('vault_users.db')
                c = conn.cursor()
                hashed_pw = hashlib.sha256(login_pass.encode()).hexdigest()
                c.execute("SELECT folder_id, is_admin FROM users WHERE username = ? AND password = ?", (login_user, hashed_pw))
                result = c.fetchone()
                conn.close()
                
                if result:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user
                    st.session_state['folder_id'] = result[0]
                    st.session_state['is_admin'] = result[1]
                    st.success("Access Granted! Synchronizing node...")
                    st.rerun()
                else:
                    st.error("Invalid credentials or node mismatch.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="tech-container">', unsafe_allow_html=True)
        st.subheader("Initialize a Sub-Vault Node")
        st.markdown("*(Requires a master-generated clearance invite code)*")
            
        with st.form("register_form"):
            reg_user = st.text_input("Choose Username")
            reg_pass = st.text_input("Choose Password", type="password")
            reg_code = st.text_input("Master Invite Clearance Code")
            reg_submit = st.form_submit_button("Initialize Node")
            
            if reg_submit:
                if not reg_user or not reg_pass or not reg_code:
                    st.warning("Please complete all parameter fields.")
                else:
                    conn = sqlite3.connect('vault_users.db')
                    c = conn.cursor()
                    
                    c.execute("SELECT is_used FROM invite_codes WHERE code = ?", (reg_code,))
                    code_res = c.fetchone()
                    
                    if not code_res:
                        st.error("Invalid clearance code.")
                    elif code_res[0] == 1:
                        st.error("This clearance code has already been burned.")
                    else:
                        c.execute("SELECT * FROM users WHERE username = ?", (reg_user,))
                        if c.fetchone():
                            st.error("Username vector already occupied.")
                        else:
                            with st.spinner("Carving out private sub-vault partition on Drive..."):
                                folder_metadata = {
                                    'name': f"{reg_user}_Vault",
                                    'mimeType': 'application/vnd.google-apps.folder',
                                    'parents': [MASTER_FOLDER_ID]
                                }
                                subfolder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                                user_folder_id = subfolder.get('id')
                                
                                hashed_pw = hashlib.sha256(reg_pass.encode()).hexdigest()
                                c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (reg_user, hashed_pw, user_folder_id, 0))
                                c.execute("UPDATE invite_codes SET is_used = 1 WHERE code = ?", (reg_code,))
                                conn.commit()
                                st.success("Vault successfully provisioned! Switch to the Login tab to enter.")
                    conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MAIN APP INTERFACE (Unlocked post-login)
# ==========================================
else:
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1:
        st.markdown(f'<div class="tech-container" style="padding: 15px 20px; margin-bottom: 15px;">', unsafe_allow_html=True)
        st.title(f"📹 {st.session_state['username'].capitalize()}'s Vault Node")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_top2:
        st.write("")
        if st.button("🚪 Terminate Session", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ''
            st.session_state['folder_id'] = ''
            st.session_state['is_admin'] = 0
            st.rerun()

    target_folder_id = st.session_state['folder_id']

    if st.session_state['is_admin'] == 1:
        with st.expander("🛠️ MASTER COMMAND MATRIX & VAULT INSPECTOR", expanded=False):
            st.markdown('<div class="tech-container">', unsafe_allow_html=True)
            st.write("### 🔑 Clearance Key Synthesizer")
            if st.button("Generate New Invite Token"):
                import uuid
                new_code = f"TRIAD-{str(uuid.uuid4()).upper()[:8]}"
                
                conn = sqlite3.connect('vault_users.db')
                c = conn.cursor()
                c.execute("INSERT INTO invite_codes VALUES (?, ?)", (new_code, 0))
                conn.commit()
                conn.close()
                
                st.success(f"Generated Clearance Code: **`{new_code}`**")
            
            conn = sqlite3.connect('vault_users.db')
            c = conn.cursor()
            c.execute("SELECT code FROM invite_codes WHERE is_used = 0")
            unused_codes = c.fetchall()
            
            if unused_codes:
                st.write("**Active Unused Clearance Tokens:**")
                for uc in unused_codes:
                    st.code(uc[0])
            else:
                st.info("No active unused clearance tokens.")

            st.markdown("---")
            st.write("### 🌐 Node Sub-Vault Inspector")
            
            c.execute("SELECT username, folder_id FROM users")
            all_users = c.fetchall()
            conn.close()
            
            user_dict = {u[0]: u[1] for u in all_users}
            selected_user_to_view = st.selectbox("Select Target Member Vault", list(user_dict.keys()))
            
            if selected_user_to_view:
                target_folder_id = user_dict[selected_user_to_view]
                if selected_user_to_view != st.session_state['username']:
                    st.info(f"🔍 Inspector active on node partition: **{selected_user_to_view}**")
            st.markdown('</div>', unsafe_allow_html=True)

    if target_folder_id == st.session_state['folder_id']:
        st.markdown('<div class="tech-container">', unsafe_allow_html=True)
        st.subheader("📤 Data Stream Ingestion")

        with st.form("upload_form", clear_on_submit=True):
            custom_title = st.text_input("Give your thought a Designated Tag Name")
            uploaded_file = st.file_uploader("Select Media Stream Package (<100MB)", type=["mp4", "mov"])
            submit_button = st.form_submit_button("Initiate Secure Upload", type="primary")

        if submit_button:
            if not uploaded_file or not custom_title:
                st.warning("Please supply both a designated tag name and a media file!")
            else:
                file_extension = os.path.splitext(uploaded_file.name)[1]
                final_name = custom_title + file_extension
                
                file_metadata = {'name': final_name, 'parents': [target_folder_id]}
                media = MediaIoBaseUpload(uploaded_file, mimetype=uploaded_file.type, chunksize=1024*1024, resumable=True)
                request = drive_service.files().create(body=file_metadata, media_body=media, fields='id')
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                response = None
                start_time = time.time()
                file_size = uploaded_file.size
                
                try:
                    while response is None:
                        status, response = request.next_chunk()
                        if status:
                            current_time = time.time()
                            current_bytes = status.resumable_progress
                            total_size = status.total_size if status.total_size else file_size
                            pct = int(current_bytes / total_size * 100) if total_size > 0 else 0
                            progress_bar.progress(min(pct, 100))
                            
                            elapsed = current_time - start_time
                            if elapsed > 0:
                                speed_mbps = (current_bytes / elapsed) / (1024 * 1024)
                                status_text.markdown(f"🚀 **Streaming...** `{pct}%` uploaded | Real-Time Velocity: `⚡ {speed_mbps:.2f} MB/s`")
                    
                    file_id = response.get('id')
                    drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
                    
                    status_text.empty()
                    progress_bar.empty()
                    st.success(f"Transmission Complete: '{final_name}' successfully locked into vault.")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Transmission stream interrupted: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tech-container">', unsafe_allow_html=True)
    st.subheader("📺 Active Vault Feed Partition")
    st.markdown('</div>', unsafe_allow_html=True)

    results = drive_service.files().list(
        q=f"'{target_folder_id}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()

    items = results.get('files', [])

    if not items:
        st.info("Target vault partition is currently empty.")
    else:
        for item in items:
            file_id = item['id']
            file_name = item['name']
            
            display_name = os.path.splitext(file_name)[0]
            
            st.markdown('<div class="glossy-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">🎬 {display_name}</div>', unsafe_allow_html=True)
            
            try:
                request = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                fh.seek(0)
                
                st.video(fh)
            except Exception as e:
                st.error(f"Stream decoder error: {e}")
            
            st.write("") 
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚨 Purge from the Triad", key=f"delete_{file_id}", type="primary", use_container_width=True):
                    drive_service.files().delete(fileId=file_id).execute()
                    st.rerun()
                    
            st.markdown('</div>', unsafe_allow_html=True)
