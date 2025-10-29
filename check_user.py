import base64
import streamlit as st
from PIL import Image
import sqlite3
import random
import string
import time
import smtplib
from email.message import EmailMessage
import io
from inference_sdk import InferenceHTTPClient

# ========== DATABASE SETUP ==========
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Users table 
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        phone TEXT,
        password TEXT
    )
''')

# History table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        result TEXT,
        confidence REAL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')
conn.commit()
conn.close()

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "logged_user" not in st.session_state:
    st.session_state.logged_user = None
  
# Session states to track screen
if "page" not in st.session_state:
    st.session_state.page = "login"

# Page setup
st.set_page_config(page_title="Palay Protector", layout="centered")

# Load logo image (make sure this path is correct)
try:
    logo = Image.open("ver 2 logo.png")
except:
    # Fallback if image not found
    logo = None

# Shared header
def show_header():
    col1, col2, col3 = st.columns([5, 3, 5])
    with col2:
        if logo:
            st.image(logo, width=150)
        else:
            st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)
    st.markdown("""
        <div style='text-align: center; font-size: 22px; font-weight: bold; color: #2e7d32;'>
            PALAY PROTECTOR
        </div>
    """, unsafe_allow_html=True)

# CSS Styling
st.markdown("""
    <style>
        .stTextInput>div>input {
            text-align: center;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            margin: 6px auto;
            display: block;
            width: 60%;
        }
        .small-button button {
            font-size: 14px;
            padding: 6px 10px;
            width: 45%;
        }
    </style>
""", unsafe_allow_html=True)

# Utility: Generate OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Utility: Send OTP Email
def send_otp_email(receiver_email, otp):
    try:
        msg = EmailMessage()
        msg['Subject'] = "Palay Protector - Your OTP Code"
        msg['From'] = "palayprotector@gmail.com"
        msg['To'] = receiver_email
        msg.set_content(f"Your OTP code is: {otp}\nValid for 5 minutes only.")

        # Gmail SMTP settings
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = "palayprotector@gmail.com"
        smtp_pass = "dfhzpiitlsgkptmg"  # ← use your generated app password (no spaces)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print(" OTP sent successfully!")
        return True
    except Exception as e:
        print(" Failed to send OTP:", e)
        return False

# Initialize Roboflow client
def init_client():
    return InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="KajReyLpzYwgJ8fJ8sVd"  # Your API key
    )

# ========== LOGIN SCREEN ==========
if st.session_state.page == "login":
    show_header()
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    # Forgot Password Button (Styled as Link)
    col1, col2 = st.columns([20, 10])
    with col2:
        if st.button("Forgot Password?", key="goto_forgot", help="Go to Forgot Password screen"):
            st.session_state.page = "otp_verification"
            st.rerun()

    if st.button("LOG IN", key="login_button"):
        if username and password:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                # Set the session state
                st.session_state.user_id = user[0]
                st.session_state.logged_user = user[1]
                st.session_state.page = "home"
                st.rerun()
            else:
                st.error("Invalid username or password")
        else:
            st.error("Please enter both username and password")

    if st.button("SIGN UP", key="signup_redirect"):
        st.session_state.page = "signup"
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ========== SIGNUP SCREEN ==========
elif st.session_state.page == "signup":
    show_header()
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown("## Create Account")

    username = st.text_input("Username", key="signup_username")
    email = st.text_input("Email", key="signup_email")
    phone = st.text_input("Phone Number", key="signup_phone")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
   

    if st.button("Create Account", key="create_account"):
        if password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, email, phone, password)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, phone, password))
                conn.commit()
                st.success("Account created successfully!")
                st.session_state.page = "login"
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Username already exists. Please choose a different one.")
            finally:
                conn.close()

    if st.button("Back to Login", key="back_to_login"):
        st.session_state.page = "login"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ========== OTP VERIFICATION SCREEN ==========
elif st.session_state.page == "otp_verification":
    show_header()
    st.markdown("## Verify via Gmail OTP")

    if "otp_stage" not in st.session_state:
        st.session_state.otp_stage = "input_email"

    # Input Email      
    if st.session_state.otp_stage == "input_email":
        input_email = st.text_input("Enter your Gmail", key="otp_email_input")

        # SEND OTP BUTTON
        if st.button("Send OTP", key="send_otp_btn"):
            if input_email:
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM users WHERE email = ?", (input_email,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    otp = generate_otp()
                    sent = send_otp_email(input_email, otp)
                    if sent:
                        st.session_state.generated_otp = otp
                        st.session_state.otp_start_time = time.time()
                        st.session_state.otp_email = input_email
                        st.session_state.verified_user = result[0]
                        st.session_state.otp_stage = "verify_otp"
                        st.rerun()
                    else:
                        st.error("Failed to send OTP.")
                else:
                    st.error("Email not found.")
        
        # ← BACK TO LOGIN BUTTON 
        if st.button("← Back to Login", key="back_to_login"):
            st.session_state.page = "login"
            st.rerun()

    # ===== Step 2: Verify OTP =====
    elif st.session_state.otp_stage == "verify_otp":
        time_left = 180 - (time.time() - st.session_state.otp_start_time)
        if time_left > 0:
            st.markdown(f"OTP expires in {int(time_left)} seconds")
        else:
            st.warning("OTP has expired. Please resend.")

        entered_otp = st.text_input("Enter OTP Code", max_chars=6)

        if st.button("Submit OTP"):
            if entered_otp == st.session_state.generated_otp and time_left > 0:
                st.success("OTP Verified!")
                st.session_state.page = "change_password"
                st.rerun()
            else:
                st.error("Invalid or expired OTP.")

        if st.button("Resend OTP"):
            now = time.time()
            if now - st.session_state.otp_start_time > 30:
                new_otp = generate_otp()
                st.session_state.generated_otp = new_otp
                st.session_state.otp_start_time = now
                sent = send_otp_email(st.session_state.otp_email, new_otp)
                if sent:
                    st.success("New OTP sent!")
                else:
                    st.error("Failed to resend OTP.")
            else:
                st.warning("Please wait before resending.")

        if st.button("Back to Email Input"):
            st.session_state.otp_stage = "input_email"
            st.rerun()

# ========== CHANGE PASSWORD SCREEN ==========
elif st.session_state.page == "change_password":
    show_header()
    st.markdown("## Change Password")

    new_password = st.text_input("New Password", type="password", key="new_password")
    confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

    if st.button("Change Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, st.session_state.otp_email))
            conn.commit()
            conn.close()
            st.success("Password changed successfully!")
            st.session_state.page = "login"
            st.rerun()

    if st.button("Back to Login", key="back_to_login"):
        st.session_state.page = "login"
        st.rerun()

# ========== HOME SCREEN ==========
# ========== HOME SCREEN ==========
elif st.session_state.page == "home":
    # Custom CSS
    st.markdown("""
    <style>
        .welcome-header {
            text-align: center;
            color: #2e7d32;
            font-size: 26px;
            font-weight: bold;
            margin-bottom: 25px;
        }
        .feature-card {
            background-color: #A8E6A1;
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-left: 5px solid #4CAF50;
            height: 180px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }
        /* Weather forecast spacing */
        .weather-section {
            margin-bottom: 40px;
        }
        
        /* Main features spacing */
        .features-section {
            margin: 40px 0;
        }
        .weather-header {
            font-size: 20px;
            font-weight: bold;
            color: #2e7d32;
            margin-bottom: 15px;
            text-align: center;
        }
        .forecast-container {
            display: flex;
            flex-direction: row;
            justify-content: flex-start;
            align-items: flex-start;
            gap: 15px;
            margin-bottom: 25px;
            overflow-x: auto;
            overflow-y: hidden;
            padding: 10px 0;
            width: 100%;
            white-space: nowrap;
        }
        .forecast-box {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            min-width: 90px;
            width: 90px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            flex-shrink: 0;
            flex-grow: 0;
            transition: transform 0.2s ease;
            display: inline-block;
            vertical-align: top;
        }
        .forecast-box:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .forecast-day {
            font-weight: bold;
            color: #1b5e20;
            margin-bottom: 6px;
            font-size: 14px;
        }
        .forecast-icon {
            width: 40px;
            height: 40px;
            margin-bottom: 5px;
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
        .forecast-temp {
            font-size: 13px;
            font-weight: bold;
            color: #333;
        }
        .temp-high {
            color: #ff5722;
        }
        .temp-low {
            color: #2196f3;
        }
        
        /* Scrollbar styling for webkit browsers */
        .forecast-container::-webkit-scrollbar {
            height: 6px;
        }
        .forecast-container::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        .forecast-container::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 10px;
        }
        .forecast-container::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        
        /* Tips section styling */
        .tips-section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #4CAF50;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .tips-title {
            font-size: 18px;
            font-weight: bold;
            color: #2e7d32;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }
        .tips-text {
            font-size: 14px;
            color: #555;
            line-height: 1.5;
        }
    </style>
    """, unsafe_allow_html=True)

    show_header()

    # Welcome message
    st.markdown(
        f"""<div class="welcome-header">
            Welcome back, <span style="color: #4CAF50;">{st.session_state.logged_user}</span>!
            <div style="font-size: 15px; color: #6c757d; margin-top: 4px;">
                Ready to protect your palay today?
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    # Weather Forecast (Demo Data)
    from datetime import datetime, timedelta

    CITY = "Manila,PH"

    def get_7day_forecast(city):
        today = datetime.now()
        temp_ranges = [
            {"max": 32, "min": 25, "icon": "01d"},  # Clear sky
            {"max": 31, "min": 24, "icon": "02d"},  # Few clouds
            {"max": 33, "min": 26, "icon": "03d"},  # Scattered clouds
            {"max": 30, "min": 25, "icon": "10d"},  # Rain
            {"max": 32, "min": 26, "icon": "01d"},  # Clear sky
            {"max": 31, "min": 25, "icon": "02d"},  # Few clouds
            {"max": 29, "min": 24, "icon": "04d"}   # Broken clouds
        ]
        forecast_data = []
        for i in range(7):
            current_date = today + timedelta(days=i)
            forecast_data.append({
                "day_short": current_date.strftime("%a"),
                "temp_max": temp_ranges[i]["max"],
                "temp_min": temp_ranges[i]["min"],
                "icon": temp_ranges[i]["icon"]
            })
        return forecast_data

    forecast = get_7day_forecast(CITY)

    # Display Forecast in Horizontal Box Layout (Left to Right)
    if forecast:
        st.markdown('<div class="weather-section">', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="weather-header">🌤️ 7-Day Weather Forecast ({CITY})</div>
        """, unsafe_allow_html=True)
        
        # Use Streamlit columns for horizontal layout
        cols = st.columns(7, gap="small")
        
        for i, day in enumerate(forecast):
            with cols[i]:
                icon_url = f"https://openweathermap.org/img/wn/{day['icon']}@2x.png"
                st.markdown(f"""
                    <div class="forecast-box">
                        <div class="forecast-day">{day['day_short']}</div>
                        <img class="forecast-icon" src="{icon_url}" alt="Weather" 
                             onerror="this.src='https://cdn-icons-png.flaticon.com/128/1163/1163661.png'">
                        <div class="forecast-temp">
                            <span class="temp-high">{day['temp_max']}°</span><br>
                            <span class="temp-low">{day['temp_min']}°</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Main features grid
    st.markdown('<div class="features-section">', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown("""
        <div class="feature-card">
            <img src="https://cdn-icons-png.flaticon.com/128/1150/1150652.png" width="70">
            <div style="font-weight: bold; margin: 8px 0;">Detect Disease</div>
            <div style="font-size: 13px;">
                Upload images of palay plants
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="detect_button", use_container_width=True):
            st.session_state.page = "detect"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="feature-card">
            <img src="https://cdn-icons-png.flaticon.com/128/12901/12901923.png" width="70">
            <div style="font-weight: bold; margin: 8px 0;">View History</div>
            <div style="font-size: 13px;">
                Check your previous scans
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="history_button", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Tips Section
    st.markdown("""
    <div class="tips-section">
        <div class="tips-title">
            <img src="https://cdn-icons-png.flaticon.com/128/1598/1598424.png" 
                 width="24" height="24" style="vertical-align: middle; margin-right: 8px;">
            Did You Know?
        </div>
        <div class="tips-text">
            Early detection of palay diseases can increase your yield by up to 30%.<br>
            Upload images weekly for best results.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Logout
    if st.button("↩ Log out", key="logout_button", help="Return to login screen"):
        st.session_state.page = "login"
        st.session_state.user_id = None
        st.session_state.logged_user = None
        st.rerun()



# ========== DETECTION SCREEN ==========
elif st.session_state.page == "detect":
    # Detection screen CSS styling
    st.markdown("""
        <style>
            .stApp {
                background: linear-gradient(135deg, #e8f5e9 0%, #ffffff 100%) !important;
            }
            .upload-section {
                background-color: #f8f9fa;
                border: 2px dashed #4CAF50;
                border-radius: 15px;
                padding: 30px;
                text-align: center;
                margin: 20px 0;
            }
            .upload-icon {
                font-size: 48px;
                color: #4CAF50;
                margin-bottom: 15px;
            }
            .upload-text {
                color: #2e7d32;
                font-size: 18px;
                font-weight: 600;
            }
            .upload-subtext {
                color: #6c757d;
                font-size: 14px;
                margin-bottom: 20px;
            }
            .preview-image {
                border-radius: 12px;
                border: 3px solid #4CAF50;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .detect-button {
                background-color: #4CAF50 !important;
                color: white !important;
                font-weight: 600 !important;
                border: none !important;
                border-radius: 25px !important;
                padding: 12px 30px !important;
                margin: 20px auto !important;
            }
            .result-box {
                background: #ffffff;
                padding: 20px;
                border-radius: 12px;
                margin: 20px 0;
                border-left: 5px solid #4CAF50;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .disease-result {
                border-left: 4px solid #ff5722 !important;
            }
            .confidence-bar {
                height: 8px;
                background: #e0e0e0;
                border-radius: 10px;
                margin: 10px 0;
            }
            .confidence-fill {
                height: 100%;
                background: linear-gradient(90deg, #ff5722, #4CAF50);
                border-radius: 10px;
            }
            .back-button {
                background-color: transparent !important;
                color: #6c757d !important;
                border: 2px solid #6c757d !important;
                margin-top: 20px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    show_header()
    
    # Page title
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='color: #2e7d32;'>Disease Detection</h2>
        <p style='color: #6c757d;'>Upload rice leaf image for analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload section with preview
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        st.markdown(f"""
    <div class="upload-section">
        <div class="upload-icon">
            <img src="https://cdn-icons-png.flaticon.com/128/19022/19022152.png" 
                 width="90" height="90" style="margin-bottom: 30px;">
        </div>
        <div class="upload-text">Upload Rice Leaf Image</div>
        <div class="upload-subtext">JPG, JPEG, or PNG (Max 5MB)</div>
        <img src="data:image/png;base64,{img_str}" class="preview-image" width="300">
    </div>
    """, unsafe_allow_html=True)

    else:
        st.markdown("""
    <div class="upload-section">
        <div class="upload-icon">
            <img src="https://cdn-icons-png.flaticon.com/128/16649/16649241.png" 
                 width="90" height="90" style="margin-bottom:30px;">
        </div>
        <div class="upload-text">Upload Rice Leaf Image</div>
        <div class="upload-subtext">JPG, JPEG, or PNG (Max 5MB)</div>
    </div>
    """, unsafe_allow_html=True)

    # Detection button
    if st.button("DETECT DISEASE", key="detect_btn"):
        if uploaded_file is None:
            st.error("Please upload an image first.")
        else:
            with st.spinner("Analyzing image..."):
                try:
                    import tempfile
                    # Save image as temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        image.save(tmp_file, format="JPEG")
                        tmp_file_path = tmp_file.name
                    
                    # Call Roboflow API with file path
                    client = init_client()
                    result = client.infer(tmp_file_path, model_id="palayprotector-project/1")
                    
                    # Display results
                    st.markdown("<div class='result-box'><h3> Results</h3>", unsafe_allow_html=True)
                    
                    if result.get("predictions"):
                        for pred in result["predictions"]:
                            disease = pred["class"]
                            confidence = pred["confidence"] * 100
                            
                            st.markdown(f"""
                            <div class='result-box disease-result'>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="font-weight: bold; color: #d32f2f;">{disease}</span>
                                    <span style="font-weight: bold; color: #2e7d32;">{confidence:.1f}%</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {confidence}%;"></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Save to history
                            conn = sqlite3.connect("users.db")
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO history (user_id, result, confidence)
                                VALUES (?, ?, ?)
                            """, (st.session_state.user_id, disease, confidence))
                            conn.commit()
                            conn.close()
                    else:
                        st.markdown("""
                        <div class='result-box'>
                            <div style="text-align: center; padding: 20px;">
                                <span style="font-size: 40px;">✅</span>
                                <h3 style="color: #2e7d32;">Healthy Rice Plant</h3>
                                <p>No diseases detected</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error during detection: {str(e)}")
    
    # Back to Home button
    if st.button("Back to Home", key="detect_back_home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

# ========== HISTORY SCREEN ==========
elif st.session_state.page == "history":
    show_header()

    # Title (mas simple, hindi sakit sa mata)
    st.markdown("""
    <div style="background:#e8f5e9; color:#1b5e20; 
                padding:10px; border-radius:8px; 
                text-align:center; margin-bottom:15px;">
        <h3 style="margin:0; font-size:18px;">Detection History</h3>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.user_id is None:
        st.warning("⚠ Please log in to view your history.")
    else:
        # Fetch from DB
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_at, result, confidence
            FROM history
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (st.session_state.user_id,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            from datetime import datetime

            # CSS + HTML
            table_html = """
            <style>
                .history-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 20px;
                    margin: 10px 0;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .history-table th {
                    background: #77dd77;
                    color: white;
                    padding: 10px;
                    text-align: center;
                }
                .history-table td {
                    padding: 10px;
                    text-align: center;
                    border-bottom: 1px solid #ddd;
                }
                .history-table tr:nth-child(even) {
                    background: #f9f9f9;
                }
                .history-table tr:hover {
                    background: #f1f8e9;
                }
                .remedy-btn {
                    background: #2e7d32;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-size: 12px;
                }
                .remedy-btn:hover {
                    background: #1b5e20;
                }
            </style>
            <table class="history-table">
                <tr>
                    <th>Date</th>
                    <th>Disease</th>
                    <th>Confidence</th>
                    <th>Action</th>
                </tr>
            """

            for date, disease, conf in rows:
                try:
                    d_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                    f_date = d_obj.strftime("%Y-%m-%d")
                except:
                    f_date = date

                table_html += f"""
                <tr>
                    <td>{f_date}</td>
                    <td>{disease}</td>
                    <td>{conf:.2f}%</td>
                    <td><a href="https://collab-app.com/dashboard?disease={disease}" 
                           target="_blank" class="remedy-btn">View Remedy</a></td>
                </tr>
                """

            table_html += "</table>"

            # ✅ Use components.html instead of markdown para sigurado render
            st.components.v1.html(table_html, height=400, scrolling=True)

        else:
            st.info("No history records yet.")

    # Back button
    if st.button("⬅ Back to Home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()