import streamlit as st
import os
import io
import sqlite3
import hashlib
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

st.set_page_config(page_title="The Triad Vault", layout="wide")

# ==========================================
# DATABASE SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect('vault_users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, password TEXT, folder_id TEXT, is_admin INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invite_codes (
                    code TEXT PRIMARY KEY, is_used INTEGER)''')
    conn.commit()
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", ('admin', hashed_pw, '1UwuA56of_7fc4WkpuUqqSZSAKsgHqEoE', 1))
        conn.commit()
    conn.close()

init_db()

# ==========================================
# CUSTOM CSS: Unique Zones & YouTube Grid
# ==========================================
st.markdown("""
<style>
/* Base Dark Theme */
.stApp {
    background: #0a0a0f;
    color: #e0e0e0;
}

/* 1. Admin Zone (Warning/Amber Theme) */
.admin-zone {
    background: linear-gradient(90deg, rgba(30,20,0,0.8), rgba(60,35,0,0.8));
    border-left: 6px solid #ffaa00;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(255, 170, 0, 0.15);
}

/* 2. Upload Zone (Cyan/Tech Theme) */
.upload-zone {
    background: linear-gradient(90deg, rgba(0,25,35,0.8), rgba(0,45,60,0.8));
    border-left: 6px solid #00eeff;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(0, 238, 255, 0.15);
}

/* 3. Feed/Player Zone (Purple/Cinematic Theme) */
.feed-header {
    background: rgba(20, 10, 40, 0.9);
    border: 1px solid rgba(150, 50, 255, 0.3);
    border-radius: 8px;
    padding: 15px 25px;
    margin-bottom: 20px;
    text-transform: uppercase;
    letter-spacing: 2px;
    text-align: center;
    box-shadow: 0 0 20px rgba(150, 50, 255, 0.2);
}

/* Video Thumbnail Cards (YouTube Style) */
.video-card {
    background: #12121a;
    border: 1px solid #2a2a35;
    border-radius: 12px;
    padding: 12px;
    transition: transform 0.2s, box-shadow 0.2s;
    height: 100%;
}
.video-card:hover {
    transform: scale(1.02);
    box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    border-color: #9632ff;
}
.card-title {
    font-size: 1.1rem;
    font-weight: bold;
    color: #ffffff;
    margin: 10px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Button Reskins */
div.stButton > button {
    border-radius: 6px;
    font-weight: bold;
    width: 100%;
}
div.stButton > button[kind="primary"] {
    background: #9632ff;
    color: white;
    border: none;
}
div.stButton > button[kind="primary"]:hover {
    background: #b05aff;
}
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
# SESSION STATE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['folder_id'] = ''
    st.session_state['is_admin'] = 0
    st.session_state['active_video_id'] = None
    st.session_state['active_video_name'] = ""

# ==========================================
# AUTHENTICATION SCREEN
# ==========================================
if not st.session_state['logged_in']:
    st.markdown('<div class="feed-header"><h2>🔐 TRIAD VAULT ACCESS</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        st.subheader("Login Node")
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Authenticate", type="primary"):
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
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="admin-zone">', unsafe_allow_html=True)
        st.subheader("Provision Node")
        with st.form("register_form"):
            reg_user = st.text_input("Choose Username")
            reg_pass = st.text_input("Choose Password", type="password")
            reg_code = st.text_input("Invite Code")
            if st.form_submit_button("Initialize Vault"):
                conn = sqlite3.connect('vault_users.db')
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
                        with st.spinner("Carving sub-vault..."):
                            folder_metadata = {'name': f"{reg_user}_Vault", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [MASTER_FOLDER_ID]}
                            subfolder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                            
                            hashed_pw = hashlib.sha256(reg_pass.encode()).hexdigest()
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (reg_user, hashed_pw, subfolder.get('id'), 0))
                            c.execute("UPDATE invite_codes SET is_used = 1 WHERE code = ?", (reg_code,))
                            conn.commit()
                            st.success("Vault provisioned! You may now login.")
                conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MAIN APP INTERFACE
# ==========================================
else:
    # Header & Logout
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.markdown(f'<div class="feed-header"><h2>📹 {st.session_state["username"].upper()}\'S VAULT</h2></div>', unsafe_allow_html=True)
    with col_t2:
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    target_folder_id = st.session_state['folder_id']

    # ==========================================
    # ADMIN ZONE (Distinct Amber)
    # ==========================================
    if st.session_state['is_admin'] == 1:
        st.markdown('<div class="admin-zone">', unsafe_allow_html=True)
        st.write("### 🛠️ MASTER COMMAND MATRIX")
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            if st.button("Generate New Invite Token"):
                import uuid
                new_code = f"TRIAD-{str(uuid.uuid4()).upper()[:8]}"
                conn = sqlite3.connect('vault_users.db')
                c = conn.cursor()
                c.execute("INSERT INTO invite_codes VALUES (?, ?)", (new_code, 0))
                conn.commit()
                conn.close()
                st.success(f"**`{new_code}`**")
        
        with col_a2:
            conn = sqlite3.connect('vault_users.db')
            c = conn.cursor()
            c.execute("SELECT username, folder_id FROM users")
            all_users = {u[0]: u[1] for u in c.fetchall()}
            conn.close()
            selected_user = st.selectbox("Inspect Node:", list(all_users.keys()))
            if selected_user:
                target_folder_id = all_users[selected_user]
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # UPLOAD ZONE (Distinct Cyan)
    # ==========================================
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
            
            submit_button = st.form_submit_button("Initiate Upload", type="primary")

        if submit_button and uploaded_file and custom_title:
            # 1. Upload Video
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
            
            # 2. Upload Thumbnail if provided (named "thumb_{video_id}.ext")
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

    # ==========================================
    # VIDEO GRID & LAZY PLAYER (YouTube Style)
    # ==========================================
    st.markdown('<div class="feed-header"><h3>📺 VAULT GRID</h3></div>', unsafe_allow_html=True)

    # Cinematic Player Engine (Only loads if a video is clicked)
    if st.session_state['active_video_id']:
        st.markdown(f"#### 🎬 Now Playing: {st.session_state['active_video_name']}")
        try:
            with st.spinner("Buffering secure stream..."):
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
        
        if st.button("❌ Close Player"):
            st.session_state['active_video_id'] = None
            st.rerun()
        st.markdown("---")

    # Fetch ALL files (videos + custom thumbnails) and include thumbnailLink
    results = drive_service.files().list(
        q=f"'{target_folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, thumbnailLink)"
    ).execute()
    items = results.get('files', [])

    # Separate videos and custom thumbnails mapping
    videos = [i for i in items if 'video/' in i.get('mimeType', '')]
    
    # Map video_id to its custom thumbnail file dictionary
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
        # Create a 3-column grid
        cols = st.columns(3)
        
        for idx, video in enumerate(videos):
            col = cols[idx % 3] # Distribute evenly across 3 columns
            
            with col:
                st.markdown('<div class="video-card">', unsafe_allow_html=True)
                
                # 1. Render Thumbnail
                vid_id = video['id']
                if vid_id in custom_thumbs:
                    # Download custom thumbnail directly into memory to display securely
                    thumb_request = drive_service.files().get_media(fileId=custom_thumbs[vid_id]['id'])
                    thumb_fh = io.BytesIO()
                    thumb_downloader = MediaIoBaseDownload(thumb_fh, thumb_request)
                    done = False
                    while not done: _, done = thumb_downloader.next_chunk()
                    thumb_fh.seek(0)
                    st.image(thumb_fh, use_container_width=True)
                elif video.get('thumbnailLink'):
                    # Use Google's auto-generated thumbnail URL if no custom one exists
                    st.image(video.get('thumbnailLink'), use_container_width=True)
                else:
                    # Fallback if Google hasn't processed the thumbnail yet
                    st.info("🎥 Processing Thumbnail...")

                # 2. Render Title & Buttons
                display_name = os.path.splitext(video['name'])[0]
                st.markdown(f'<div class="card-title">{display_name}</div>', unsafe_allow_html=True)
                
                button_col1, button_col2 = st.columns([2, 1])
                with button_col1:
                    if st.button("▶️ Watch", key=f"play_{vid_id}", type="primary"):
                        st.session_state['active_video_id'] = vid_id
                        st.session_state['active_video_name'] = display_name
                        st.rerun()
                with button_col2:
                    if st.button("🗑️", key=f"del_{vid_id}"):
                        drive_service.files().delete(fileId=vid_id).execute()
                        # Also delete custom thumbnail if it exists to save space
                        if vid_id in custom_thumbs:
                            drive_service.files().delete(fileId=custom_thumbs[vid_id]['id']).execute()
                        if st.session_state['active_video_id'] == vid_id:
                            st.session_state['active_video_id'] = None
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
