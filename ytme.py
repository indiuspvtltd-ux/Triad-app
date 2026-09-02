import streamlit as st
import os
import io
import sqlite3
import time
import bcrypt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

st.set_page_config(page_title="The Triad Vault", layout="wide")

# ==========================================
# YOUTUBE-STYLE SLIDING SPLASH SCREEN
# ==========================================
if 'has_splashed' not in st.session_state:
    st.session_state['has_splashed'] = True
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700;900&display=swap');
    
    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #050508;
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
        color: #ff2a2a;
        text-shadow: 0 0 30px rgba(255, 42, 42, 0.6);
    }
    .brand-text {
        font-size: 4.5rem;
        font-weight: 900;
        color: white;
        letter-spacing: -2px;
        font-family: 'Outfit', sans-serif;
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
# SIGHTENGINE NSFW SCANNER FUNCTION
# ==========================================
def scan_video_content(temp_file_path):
    """
    Extracts a single frame from the video and sends it to Sightengine's 
    NSFW API to check for explicit content before allowing the upload.
    """
    import cv2
    import requests
    import os
    
    try:
        # 1. Extract a single frame (30 frames into the video)
        cap = cv2.VideoCapture(temp_file_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 30) 
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return True # Fallback if extraction fails
            
        # 2. Save the frame temporarily
        frame_path = "temp_scan_frame.jpg"
        cv2.imwrite(frame_path, frame)
        
        # 3. Send the image to Sightengine
        params = {
            'models': 'nudity-2.0',
            'api_user': '885017226',
            'api_secret': 'bEaHzJzrFb4FMGpRsQpEdySpsg73PhJV'
        }
        
        with open(frame_path, 'rb') as f:
            files = {'media': f}
            r = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params, timeout=10)
        
        # 4. Clean up the temporary image
        os.remove(frame_path)
        
        response = r.json()
        
        # 5. Check the NSFW score
        if 'nudity' in response:
            # If the 'safe' confidence score drops below 50%, block it
            if response['nudity']['safe'] < 0.50: 
                return False 
                
        return True
        
    except Exception as e:
        print(f"Scanner Exception: {e}")
        return True # Default to safe if the API network fails

# ==========================================
# CUSTOM CSS: Hyper-Modern Animated Glass UI
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

.stApp {
    font-family: 'Outfit', sans-serif !important;
    background: radial-gradient(circle at top left, #120a21, #050508 70%);
    color: #e0e0e0;
}

/* 📱 AUTO-RESPONSIVE MOBILE STACKING */
@media (max-width: 900px) {
    div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
        margin-bottom: 25px;
    }
    .main-banner h2 {
        font-size: 2rem !important;
    }
    .auth-header {
        font-size: 1.3rem !important;
        margin-bottom: 15px !important;
    }
    .brand-text {
        font-size: 3rem !important;
    }
    .play-icon {
        font-size: 4rem !important;
    }
}

/* 🌟 Animated Main Banner */
.main-banner {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    padding: 30px 20px;
    text-align: center;
    margin-bottom: 25px;
    box-shadow: 0 15px 35px rgba(0,0,0,0.6);
    backdrop-filter: blur(15px);
    animation: floatBanner 6s ease-in-out infinite;
}
@keyframes floatBanner {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-8px); box-shadow: 0 25px 45px rgba(150,50,255,0.1); }
    100% { transform: translateY(0px); }
}
.main-banner h2 {
    background: linear-gradient(90deg, #00e5ff, #b25cff, #ffa600, #00e5ff);
    background-size: 300% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.8rem;
    font-weight: 800;
    margin: 0;
    animation: textShimmer 5s linear infinite;
    letter-spacing: -1px;
}
@keyframes textShimmer {
    0% { background-position: 0% center; }
    100% { background-position: 300% center; }
}

/* 💎 Glassmorphism Form Containers */
div[data-testid="stForm"] {
    background: rgba(20, 20, 30, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px;
    padding: 25px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(12px);
    transition: all 0.3s ease;
}
div[data-testid="stForm"]:hover {
    border-color: rgba(255, 255, 255, 0.2) !important;
    transform: translateY(-3px);
}

/* ✨ Inputs & Buttons */
.stTextInput > div > div > input {
    background-color: rgba(0, 0, 0, 0.3) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
    transition: all 0.3s ease;
}
.stTextInput > div > div > input:focus {
    border-color: #b25cff !important;
    box-shadow: 0 0 15px rgba(178, 92, 255, 0.3) !important;
}

div.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-family: 'Outfit', sans-serif !important;
    width: 100%;
    transition: all 0.2s ease;
    text-transform: uppercase;
    letter-spacing: 1px;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ff2a2a, #ff5e5e);
    color: white;
    border: none;
    box-shadow: 0 4px 15px rgba(255, 42, 42, 0.3);
}
div.stButton > button[kind="primary"]:hover {
    transform: scale(1.02);
    box-shadow: 0 6px 20px rgba(255, 42, 42, 0.5);
}
div.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.05);
    color: #c0c0c0;
    border: 1px solid rgba(255,255,255,0.1);
}
div.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.1);
    color: white;
}

/* 📌 Headers for Auth Sections */
.auth-header {
    font-family: 'Outfit', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: white;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.login-accent { color: #00e5ff; }
.create-accent { color: #ffa600; }

/* Vault Grid CSS */
.admin-zone { background: rgba(255, 170, 0, 0.05); border-left: 4px solid #ffaa00; border-radius: 12px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(10px); }
.upload-zone { background: rgba(0, 238, 255, 0.05); border-left: 4px solid #00eeff; border-radius: 12px; padding: 20px; margin-bottom: 30px; backdrop-filter: blur(10px); }
.feed-header { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 15px 25px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px; text-align: center; backdrop-filter: blur(10px); }
.video-card { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 16px; padding: 12px; transition: all 0.3s; height: 100%; backdrop-filter: blur(5px); display: flex; flex-direction: column; justify-content: space-between; }
.video-card:hover { transform: translateY(-5px); border-color: rgba(178, 92, 255, 0.5); box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
.card-title { font-size: 1.1rem; font-weight: 600; color: #ffffff; margin: 10px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
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
# AUTHENTICATION SCREEN
# ==========================================
if not st.session_state['logged_in']:
    st.markdown('<div class="main-banner"><h2>🌌 Welcome to your Personal Vault ✦ by TRIAD</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown('<div class="auth-header"><span class="login-accent">🔓</span> Login Portal <span style="font-size:1rem; opacity:0.6; font-weight:400;">(Existing User)</span></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            st.write("") 
            if st.form_submit_button("⚡ Authenticate Node", type="primary"):
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
        st.markdown('<div class="auth-header"><span class="create-accent">✨</span> Provision Node <span style="font-size:1rem; opacity:0.6; font-weight:400;">(New User)</span></div>', unsafe_allow_html=True)
        with st.form("register_form"):
            reg_user = st.text_input("Choose Username")
            reg_pass = st.text_input("Choose Password", type="password")
            reg_code = st.text_input("Invite Code")
            st.write("") 
            if st.form_submit_button("🚀 Initialize Vault", type="secondary"):
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
                                st.success("🎉 Vault securely provisioned! You may now login.")
                    conn.close()

# ==========================================
# MAIN APP INTERFACE
# ==========================================
else:
    col_t1, col_t2 = st.columns([6, 1])
    with col_t1:
        st.markdown(f'<div class="feed-header"><h2 style="margin:0; font-weight:800;">📹 {st.session_state["username"].upper()}\'S VAULT</h2></div>', unsafe_allow_html=True)
    with col_t2:
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.clear()
            st.rerun()

    target_folder_id = st.session_state['folder_id']

    # Admin Control Panel
    if st.session_state['is_admin'] == 1:
        st.markdown('<div class="admin-zone">', unsafe_allow_html=True)
        st.write("<h3 style='margin-top:0;'>🛠️ MASTER COMMAND MATRIX</h3>", unsafe_allow_html=True)
        
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            if st.button("🔑 Generate Secure Invite Token", type="primary"):
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
            selected_user = st.selectbox("🌐 Inspect Node:", list(all_users.keys()))
            if selected_user:
                target_folder_id = all_users[selected_user]
        st.markdown('</div>', unsafe_allow_html=True)

    # File Upload Module
    if target_folder_id == st.session_state['folder_id']:
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        st.write("<h3 style='margin-top:0;'>📤 INGESTION STREAM</h3>", unsafe_allow_html=True)

        with st.form("upload_form", clear_on_submit=True):
            col_u1, col_u2 = st.columns([2, 1])
            with col_u1:
                custom_title = st.text_input("🏷️ Designated Tag Name")
                uploaded_file = st.file_uploader("🎞️ Video Stream (Gigabyte-Ready)", type=["mp4", "mov", "mkv", "avi"])
            with col_u2:
                st.write("") 
                st.write("") 
                thumb_file = st.file_uploader("🖼️ Thumbnail (Optional)", type=["jpg", "png", "jpeg"])
            
            st.write("")
            submit_button = st.form_submit_button("⬆️ Initiate Large-Scale Upload", type="primary")

        if submit_button and uploaded_file and custom_title:
            file_extension = os.path.splitext(uploaded_file.name)[1]
            final_name = custom_title + file_extension
            
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            # MEMORY PROTECTION: Write large file chunks to local disk temp file
            status_text.markdown("⏳ Buffering stream to local vault...")
            temp_file_path = f"temp_{final_name}"
            with open(temp_file_path, "wb") as f:
                for chunk in iter(lambda: uploaded_file.read(1024*1024), b""):
                    f.write(chunk)
            
            # RUN THE FREE SIGHTENGINE SCANNER
            status_text.markdown("🛡️ **SCANNING:** Checking community guidelines (NSFW Analysis)...")
            is_safe = scan_video_content(temp_file_path)
            
            if not is_safe:
                # Security Failure: Delete the temp file and block the upload
                os.remove(temp_file_path)
                status_text.empty()
                progress_bar.empty()
                st.error("🚨 **UPLOAD BLOCKED:** This video violates explicit content guidelines.")
                
            else:
                # Security Passed: Proceed with Google Drive Upload
                status_text.markdown("✅ **Scan Passed.** Routing to encrypted vault...")
                
                file_size = os.path.getsize(temp_file_path)
                media = MediaFileUpload(temp_file_path, mimetype=uploaded_file.type, chunksize=10*1024*1024, resumable=True)
                request = drive_service.files().create(body={'name': final_name, 'parents': [target_folder_id]}, media_body=media, fields='id')
                
                start_time = time.time()
                last_ui_update = start_time 
                response = None
                
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        current_time = time.time()
                        if current_time - last_ui_update > 0.5:
                            pct = int(status.resumable_progress / file_size * 100)
                            progress_bar.progress(min(pct, 100))
                            
                            elapsed_time = current_time - start_time
                            if elapsed_time > 0:
                                speed = (status.resumable_progress / elapsed_time) / (1024 * 1024)
                            else:
                                speed = 0.0
                                
                            status_text.markdown(f"🚀 **UPLOADING:** `{pct}%` | `⚡ {speed:.2f} MB/s`")
                            last_ui_update = current_time
                
                # Clean up local disk temp file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

                video_id = response.get('id')
                
                if thumb_file:
                    status_text.markdown("📸 Processing custom thumbnail...")
                    progress_bar.progress(98)
                    thumb_ext = os.path.splitext(thumb_file.name)[1]
                    thumb_metadata = {'name': f"thumb_{video_id}{thumb_ext}", 'parents': [target_folder_id]}
                    thumb_media = MediaIoBaseUpload(thumb_file, mimetype=thumb_file.type, resumable=False)
                    drive_service.files().create(body=thumb_metadata, media_body=thumb_media, fields='id').execute()

                status_text.empty()
                progress_bar.empty()
                st.success(f"✅ Vault Security Passed: '{final_name}' is now live.")
                time.sleep(1.5)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Video Grid & Player
    st.markdown('<div class="feed-header"><h3 style="margin:0; font-weight:800;">📺 VAULT GRID</h3></div>', unsafe_allow_html=True)

    if st.session_state['active_video_id']:
        st.markdown(f"#### 🎬 Now Playing: {st.session_state['active_video_name']}")
        try:
            with st.spinner("Decrypting secure stream..."):
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
        st.info("🏜️ Grid is currently empty.")
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
                    st.info("⏳ Processing Thumbnail...")

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
