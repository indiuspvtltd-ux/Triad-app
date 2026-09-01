import streamlit as st
import os
import io
import sqlite3
import time
import bcrypt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

st.set_page_config(page_title="The Triad Vault", layout="wide")

# ==========================================
# YOUTUBE-STYLE SLIDING SPLASH SCREEN
# ==========================================
if 'has_splashed' not in st.session_state:
    st.session_state['has_splashed'] = True
    st.markdown("""
    <style>
    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #0a0a0f;
        z-index: 999999;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: slideOut 2.2s cubic-bezier(0.8, 0, 0.2, 1) forwards;
        pointer-events: none;
    }
    .splash-logo {
        display: flex;
        align-items: center;
        gap: 15px;
        animation: logoPulse 1.2s ease-in-out forwards;
    }
    .play-icon {
        font-size: 6rem;
        color: #ff0000;
        text-shadow: 0 0 20px rgba(255, 0, 0, 0.4);
    }
    .brand-text {
        font-size: 4rem;
        font-weight: 900;
        color: white;
        letter-spacing: -2px;
        font-family: 'Arial', sans-serif;
    }
    @keyframes slideOut {
        0% { transform: translateY(0); opacity: 1; }
        75% { transform: translateY(0); opacity: 1; }
        100% { transform: translateY(-100vh); opacity: 0; display: none; }
    }
    @keyframes logoPulse {
        0% { transform: scale(0.5); opacity: 0; }
        40% { transform: scale(1.1); opacity: 1; }
        60% { transform: scale(1); opacity: 1; }
        100% { transform: scale(1); opacity: 1; }
    }
    </style>
    <div id="splash-screen">
        <div class="splash-logo">
            <span class="play-icon">▶</span>
            <span class="brand-text">TRIAD</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# HARDENED DATABASE SETUP (v2)
# ==========================================
def init_db():
    conn = sqlite3.connect('vault_users_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, 
                    password TEXT, 
                    folder_id TEXT, 
                    is_admin INTEGER,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invite_codes (
                    code TEXT PRIMARY KEY, is_used INTEGER)''')
    conn.commit()
    
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        salt = bcrypt.gensalt()
        hashed_pw = bcrypt.hashpw('admin123'.encode('utf-8'), salt).decode('utf-8')
        c.execute("INSERT INTO users (username, password, folder_id, is_admin, failed_attempts, locked_until) VALUES (?, ?, ?, ?, ?, ?)", 
                  ('admin', hashed_pw, '1UwuA56of_7fc4WkpuUqqSZSAKsgHqEoE', 1, 0, 0))
        conn.commit()
    conn.close()

init_db()

# ==========================================
# CUSTOM CSS: Auth Mockup & Vault Theme
# ==========================================
st.markdown("""
<style>
.stApp { background: #0a0a0f; color: #e0e0e0; }

/* Main Screen Authentic Mockup CSS */
.main-banner {
    background: #11081a;
    border: 1px solid rgba(130, 50, 200, 0.2);
    border-radius: 8px;
    padding: 35px;
    text-align: center;
    margin-bottom: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}
.main-banner h2 {
    color: #ffffff;
    font-size: 2.3rem;
    font-weight: 700;
    margin: 0;
}
.login-header {
    background: linear-gradient(90deg, #091a24, #050d12);
    border-left: 8px solid #00e5ff;
    border-radius: 6px;
    padding: 15px 25px;
    font-size: 1.5rem;
    font-weight: 700;
    color: white;
    text-align: center;
    margin-bottom: 15px;
}
.create-header {
    background: linear-gradient(90deg, #241705, #140d05);
    border-left: 8px solid #ffa600;
    border-radius: 6px;
    padding: 15px 25px;
    font-size: 1.5rem;
    font-weight: 700;
    color: white;
    text-align: center;
    margin-bottom: 15px;
}
div[data-testid="stForm"] {
    background-color: #121216 !important;
    border: 1px solid #2a2a35 !important;
    border-radius: 10px;
    padding: 20px;
}
.stTextInput > div > div > input {
    background-color: #1e1e24 !important;
    border: 1px solid #333 !important;
    color: white !important;
    border-radius: 6px !important;
}

/* Vault Grid CSS */
.admin-zone { background: linear-gradient(90deg, rgba(30,20,0,0.8), rgba(60,35,0,0.8)); border-left: 6px solid #ffaa00; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.upload-zone { background: linear-gradient(90deg, rgba(0,25,35,0.8), rgba(0,45,60,0.8)); border-left: 6px solid #00eeff; border-radius: 8px; padding: 20px; margin-bottom: 30px; }
.feed-header { background: rgba(20, 10, 40, 0.9); border: 1px solid rgba(150, 50, 255, 0.3); border-radius: 8px; padding: 15px 25px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px; text-align: center; }
.video-card { background: #12121a; border: 1px solid #2a2a35; border-radius: 12px; padding: 12px; transition: transform 0.2s, box-shadow 0.2s; height: 100%; }
.video-card:hover { transform: scale(1.02); border-color: #9632ff; }
.card-title { font-size: 1.1rem; font-weight: bold; color: #ffffff; margin: 10px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Buttons */
div.stButton > button { border-radius: 6px; font-weight: bold; width: 100%; }
div.stButton > button[kind="primary"] { background: #ff4b4b; color: white; border: none; }
div.stButton > button[kind="secondary"] { background: #1a1a24; color: #a0a0a0; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# GOOGLE DRIVE OAUTH SETUP
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = None

if "google_token" in st.secrets:
    creds_info = dict(st.secrets["google_token"])
    creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
elif os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())

drive_service = build('drive', 'v3', credentials=creds)
MASTER_FOLDER_ID = '1UwuA56of_7fc4WkpuUqqSZSAKsgHqEoE'

# ==========================================
# SECURE SESSION STATE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['folder_id'] = ''
    st.session_state['is_admin'] = 0
    st.session_state['active_video_id'] = None
    st.session_state['active_video_name'] = ""

# ==========================================
# AUTHENTICATION SCREEN (Custom Mockup Layout)
# ==========================================
if not st.session_state['logged_in']:
    st.markdown('<div class="main-banner"><h2>welcome to ur personal vault ~~ by triad</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown('<div class="login-header">login (existing user)</div>', unsafe_allow_html=True)
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Authenticate", type="primary"):
                conn = sqlite3.connect('vault_users_v2.db')
                c = conn.cursor()
                c.execute("SELECT password, folder_id, is_admin, failed_attempts, locked_until FROM users WHERE username = ?", (login_user,))
                result = c.fetchone()
                
                if result:
                    stored_hash, folder_id, is_admin, failed_attempts, locked_until = result
                    current_time = time.time()
                    
                    if locked_until > current_time:
                        remaining_mins = int((locked_until - current_time) / 60)
                        st.error(f"🚨 Security Trigger: Account locked. Try again in {remaining_mins} minutes.")
                    else:
                        if bcrypt.checkpw(login_pass.encode('utf-8'), stored_hash.encode('utf-8')):
                            c.execute("UPDATE users SET failed_attempts = 0, locked_until = 0 WHERE username = ?", (login_user,))
                            conn.commit()
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = login_user
                            st.session_state['folder_id'] = folder_id
                            st.session_state['is_admin'] = is_admin
                            st.rerun()
                        else:
                            new_attempts = failed_attempts + 1
                            if new_attempts >= 5:
                                lock_time = current_time + 900
                                c.execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?", (new_attempts, lock_time, login_user))
                                st.error("🚨 Account Locked. Try again in 15 minutes.")
                            else:
                                c.execute("UPDATE users SET failed_attempts = ? WHERE username = ?", (new_attempts, login_user))
                                st.error(f"❌ Invalid password. {5 - new_attempts} attempts remaining.")
                            conn.commit()
                else:
                    st.error("❌ Invalid credentials.")
                conn.close()

    with col2:
        st.markdown('<div class="create-header">create vault (new user)</div>', unsafe_allow_html=True)
        with st.form("register_form"):
            reg_user = st.text_input("Choose Username")
            reg_pass = st.text_input("Choose Password", type="password")
            reg_code = st.text_input("Invite Code")
            # Defaults to secondary styling (dark grey outline) as shown in the mockup
            if st.form_submit_button("Initialize Vault"):
                if len(reg_pass) < 6:
                    st.warning("Password must be at least 6 characters long.")
                else:
                    conn = sqlite3.connect('vault_users_v2.db')
                    c = conn.cursor()
                    c.execute("SELECT is_used FROM invite_codes WHERE code = ?", (reg_code,))
                    code_res = c.fetchone()
                    
                    if not code_res or code_res[0] == 1:
                        st.error("Invalid or used code.")
                    else:
                        c.execute("SELECT * FROM users WHERE username = ?", (reg_user,))
                        if c.fetchone():
                            st.error("Username taken.")
                        else:
                            with st.spinner("Carving sub-vault & encrypting credentials..."):
                                folder_metadata = {'name': f"{reg_user}_Vault", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [MASTER_FOLDER_ID]}
                                subfolder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                                
                                salt = bcrypt.gensalt()
                                hashed_pw = bcrypt.hashpw(reg_pass.encode('utf-8'), salt).decode('utf-8')
                                
                                c.execute("INSERT INTO users (username, password, folder_id, is_admin, failed_attempts, locked_until) VALUES (?, ?, ?, ?, ?, ?)", 
                                          (reg_user, hashed_pw, subfolder.get('id'), 0, 0, 0))
                                c.execute("UPDATE invite_codes SET is_used = 1 WHERE code = ?", (reg_code,))
                                conn.commit()
                                st.success("Vault securely provisioned! You may now login.")
                    conn.close()

# ==========================================
# MAIN APP INTERFACE
# ==========================================
else:
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.markdown(f'<div class="feed-header"><h2>📹 {st.session_state["username"].upper()}\'S VAULT</h2></div>', unsafe_allow_html=True)
    with col_t2:
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.clear()
            st.rerun()

    target_folder_id = st.session_state['folder_id']

    if st.session_state['is_admin'] == 1:
        st.markdown('<div class="admin-zone">', unsafe_allow_html=True)
        st.write("### 🛠️ MASTER COMMAND MATRIX")
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            if st.button("Generate Secure Invite Token", type="primary"):
                import uuid
                new_code = f"TRIAD-{str(uuid.uuid4()).upper()[:8]}"
                conn = sqlite3.connect('vault_users_v2.db')
                c = conn.cursor()
                c.execute("INSERT INTO invite_codes VALUES (?, ?)", (new_code, 0))
                conn.commit()
                conn.close()
                st.success(f"**`{new_code}`**")
        
        with col_a2:
            conn = sqlite3.connect('vault_users_v2.db')
            c = conn.cursor()
            c.execute("SELECT username, folder_id FROM users")
            all_users = {u[0]: u[1] for u in c.fetchall()}
            conn.close()
            selected_user = st.selectbox("Inspect Node:", list(all_users.keys()))
            if selected_user:
                target_folder_id = all_users[selected_user]
        st.markdown('</div>', unsafe_allow_html=True)

    if target_folder_id == st.session_state['folder_id']:
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        st.write("### 📤 INGESTION STREAM")

        with st.form("upload_form", clear_on_submit=True):
            col_u1, col_u2 = st.columns([2, 1])
            with col_u1:
                custom_title = st.text_input("Designated Tag Name")
                uploaded_file = st.file_uploader("Video Stream (<100MB)", type=["mp4", "mov"])
            with col_u2:
                st.write("") 
                st.write("") 
                thumb_file = st.file_uploader("Thumbnail (Optional)", type=["jpg", "png", "jpeg"])
            
            submit_button = st.form_submit_button("Initiate Encrypted Upload", type="primary")

        if submit_button and uploaded_file and custom_title:
            file_extension = os.path.splitext(uploaded_file.name)[1]
            final_name = custom_title + file_extension
            media = MediaIoBaseUpload(uploaded_file, mimetype=uploaded_file.type, chunksize=1024*1024, resumable=True)
            request = drive_service.files().create(body={'name': final_name, 'parents': [target_folder_id]}, media_body=media, fields='id')
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            response, start_time = None, time.time()
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.resumable_progress / uploaded_file.size * 100)
                    progress_bar.progress(min(pct, 100))
                    speed = (status.resumable_progress / (time.time() - start_time)) / (1024 * 1024)
                    status_text.markdown(f"🚀 `{pct}%` | `⚡ {speed:.2f} MB/s`")
            
            video_id = response.get('id')
            drive_service.permissions().create(fileId=video_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            
            if thumb_file:
                status_text.markdown("📸 Processing custom thumbnail...")
                thumb_ext = os.path.splitext(thumb_file.name)[1]
                thumb_metadata = {'name': f"thumb_{video_id}{thumb_ext}", 'parents': [target_folder_id]}
                thumb_media = MediaIoBaseUpload(thumb_file, mimetype=thumb_file.type, resumable=True)
                thumb_resp = drive_service.files().create(body=thumb_metadata, media_body=thumb_media, fields='id').execute()
                drive_service.permissions().create(fileId=thumb_resp.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()

            status_text.empty()
            progress_bar.empty()
            st.success(f"'{final_name}' locked into vault.")
            time.sleep(1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="feed-header"><h3>📺 VAULT GRID</h3></div>', unsafe_allow_html=True)

    if st.session_state['active_video_id']:
        st.markdown(f"#### 🎬 Now Playing: {st.session_state['active_video_name']}")
        try:
            with st.spinner("Decrypting stream..."):
                request = drive_service.files().get_media(fileId=st.session_state['active_video_id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                fh.seek(0)
                st.video(fh)
        except Exception as e:
            st.error(f"Stream decoder error: {e}")
        
        if st.button("❌ Close Player", type="secondary"):
            st.session_state['active_video_id'] = None
            st.rerun()
        st.markdown("---")

    results = drive_service.files().list(
        q=f"'{target_folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, thumbnailLink)"
    ).execute()
    items = results.get('files', [])

    videos = [i for i in items if 'video/' in i.get('mimeType', '')]
    custom_thumbs = {}
    for i in items:
        if i['name'].startswith('thumb_'):
            try:
                vid_id = i['name'].split('_')[1].split('.')[0]
                custom_thumbs[vid_id] = i
            except:
                pass

    if not videos:
        st.info("Grid is currently empty.")
    else:
        cols = st.columns(3)
        for idx, video in enumerate(videos):
            col = cols[idx % 3]
            
            with col:
                st.markdown('<div class="video-card">', unsafe_allow_html=True)
                
                vid_id = video['id']
                if vid_id in custom_thumbs:
                    thumb_request = drive_service.files().get_media(fileId=custom_thumbs[vid_id]['id'])
                    thumb_fh = io.BytesIO()
                    thumb_downloader = MediaIoBaseDownload(thumb_fh, thumb_request)
                    done = False
                    while not done: _, done = thumb_downloader.next_chunk()
                    thumb_fh.seek(0)
                    st.image(thumb_fh, use_container_width=True)
                elif video.get('thumbnailLink'):
                    st.image(video.get('thumbnailLink'), use_container_width=True)
                else:
                    st.info("🎥 Processing Thumbnail...")

                display_name = os.path.splitext(video['name'])[0]
                st.markdown(f'<div class="card-title">{display_name}</div>', unsafe_allow_html=True)
                
                button_col1, button_col2 = st.columns([2, 1])
                with button_col1:
                    if st.button("▶️ Watch", key=f"play_{vid_id}", type="primary"):
                        st.session_state['active_video_id'] = vid_id
                        st.session_state['active_video_name'] = display_name
                        st.rerun()
                with button_col2:
                    if st.button("🗑️", key=f"del_{vid_id}", type="secondary"):
                        drive_service.files().delete(fileId=vid_id).execute()
                        if vid_id in custom_thumbs:
                            drive_service.files().delete(fileId=custom_thumbs[vid_id]['id']).execute()
                        if st.session_state['active_video_id'] == vid_id:
                            st.session_state['active_video_id'] = None
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
