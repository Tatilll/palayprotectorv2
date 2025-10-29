# ========== IMPORTS ==========
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
import pandas as pd

import streamlit as st

st.markdown("""
<style>
/* Make entire app responsive */
[data-testid="stAppViewContainer"] {
    padding: 0.5rem !important;
    overflow-x: hidden !important;
}

/* Force widgets and cards to be full width on mobile */
.stButton button,
.stFileUploader,
.stTextInput input,
div[data-testid="stVerticalBlock"] > div {
    width: 100% !important;
}

/* Reduce excessive height and spacing */
button {
    padding: 0.5rem 0.8rem !important;
    font-size: 1rem !important;
}

/* Make all images scale nicely */
img {
    max-width: 100% !important;
    height: auto !important;
}

/* Center text and icons */
.stMarkdown, .stButton, .stImage {
    text-align: center !important;
}

/* Specific tweaks for small screens */
@media (max-width: 768px) {
    .block-container {
        padding: 0.5rem !important;
    }

    .stButton button {
        display: block !important;
        margin: 0.3rem auto !important;
    }

    /* Make icons and text in cards smaller */
    svg, img {
        width: 60px !important;
        height: 60px !important;
    }

    p, h1, h2, h3, h4 {
        font-size: 0.9rem !important;
    }
}
</style>
""", unsafe_allow_html=True)



# ========== HELPER FUNCTIONS ==========
def generate_otp(length=6):
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(receiver_email, otp):
    """Send OTP via email"""
    try:
        msg = EmailMessage()
        msg['Subject'] = "Palay Protector - Your OTP Code"
        msg['From'] = "palayprotector@gmail.com"
        msg['To'] = receiver_email
        msg.set_content(f"Your OTP code is: {otp}\nValid for 5 minutes only.")

        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = "palayprotector@gmail.com"
        smtp_pass = "dfhzpiitlsgkptmg"

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print("OTP sent successfully!")
        return True
    except Exception as e:
        print("Failed to send OTP:", e)
        return False

def init_client():
    """Initialize Roboflow client for disease detection"""
    return InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="KajReyLpzYwgJ8fJ8sVd"
    )

def show_bottom_nav(active_page):
    """Display bottom navigation bar"""
    st.markdown('<div class="bottom-nav-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="nav-box {'active' if active_page == 'home' else ''}">
                <img src="https://cdn-icons-png.flaticon.com/128/1946/1946488.png" class="nav-icon-img" alt="Home">
            </div>
        """, unsafe_allow_html=True)
        if st.button("Home", key="btn_nav_home"):
            st.session_state.page = "home"
            st.rerun()
    
    with col2:
        st.markdown(f"""
            <div class="nav-box {'active' if active_page == 'library' else ''}">
                <img src="https://cdn-icons-png.flaticon.com/128/2702/2702154.png" class="nav-icon-img" alt="Library">
            </div>
        """, unsafe_allow_html=True)
        if st.button("Library", key="btn_nav_library"):
            st.session_state.page = "library"
            st.rerun()
    
    with col3:
        st.markdown(f"""
            <div class="nav-box {'active' if active_page == 'profile' else ''}">
                <img src="https://cdn-icons-png.flaticon.com/128/1077/1077114.png" class="nav-icon-img" alt="Profile">
            </div>
        """, unsafe_allow_html=True)
        if st.button("Profile", key="btn_nav_profile"):
            st.session_state.page = "profile"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ========== DATABASE SETUP ==========
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        phone TEXT,
        password TEXT,
        user_type TEXT DEFAULT 'farmer'
    )
''')

# Add user_type column if it doesn't exist (for existing databases)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN user_type TEXT DEFAULT 'farmer'")
    conn.commit()
    print("Added user_type column to existing database")
except sqlite3.OperationalError:
    # Column already exists
    pass

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

# ========== SESSION STATE INITIALIZATION ==========
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "logged_user" not in st.session_state:
    st.session_state.logged_user = None

if "user_type" not in st.session_state:
    st.session_state.user_type = None
  
if "page" not in st.session_state:
    st.session_state.page = "login"

# Handle bottom nav clicks
query_params = st.query_params
if 'nav' in query_params:
    nav_page = query_params['nav'][0]
    if nav_page in ['home', 'detect', 'library', 'profile', 'history', 'admin_dashboard']:
        st.session_state.page = nav_page
        st.query_params.clear()
        st.rerun()

# ========== PAGE SETUP ==========
st.set_page_config(page_title="Palay Protector", layout="centered")

# ========== CSS STYLING ==========
st.markdown("""
<style>
    footer {visibility: hidden;}
    .main footer {display: none !important;}
    
    .main > .block-container {
        padding-bottom: 120px !important;
        margin-bottom: 0 !important;
    }
    
    [data-testid="stAppViewContainer"] {
        padding-bottom: 100px !important;
    }
    
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .user-type-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 8px;
    }
    
    .badge-farmer {
        background-color: #4CAF50;
        color: white;
    }
    
    .badge-admin {
        background-color: #FF5722;
        color: white;
    }
    
    .user-type-box {
        display: flex;
        align-items: center;
        padding: 12px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        margin: 10px 0;
        background: white;
    }
    
    .user-type-box img {
        width: 32px;
        height: 32px;
        margin-right: 12px;
    }
    
    .user-type-box.selected {
        border-color: #4CAF50;
        background-color: #f1f8f4;
    }
    
    .icon-small {
        width: 20px;
        height: 20px;
        vertical-align: middle;
        margin-right: 6px;
    }
    
    .icon-medium {
        width: 40px;
        height: 40px;
        margin-bottom: 8px;
    }
    
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        width: 100%;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        border: 2px solid #e0e0e0;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #2e7d32;
        margin: 10px 0;
    }
    
    .metric-label {
        font-size: 14px;
        color: #666;
    }
    
    /* Bottom Navigation Styling */
    .bottom-nav-container {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 600px;
        max-width: 90%;
        background-color: white;
        padding: 15px 10px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        border-radius: 20px 20px 0 0;
        z-index: 999999 !important;
    }
    
    .nav-box {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 8px;
    }
    
    .nav-box.active {
        border-color: #4CAF50;
        background-color: #e8f5e9;
        border-width: 3px;
    }
    
    .nav-icon-img {
        width: 36px;
        height: 36px;
    }
</style>
""", unsafe_allow_html=True)

# ========== LOAD LOGO ==========
try:
    logo = Image.open("ver 2.0 logo.png")
except:
    logo = None

# ========== SHARED HEADER ==========
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

# ========================================
# PAGE ROUTING
# ========================================

# ========== LOGIN PAGE ==========
if st.session_state.page == "login":
    show_header()
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # User Type Radio Buttons (Checklist style)
    st.markdown("**Login as:**")
    user_type = st.radio(
        "Select user type",
        ["Farmer", "Admin"],
        key="login_user_type",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Username Input
    username = st.text_input("Username", key="login_username", placeholder="Enter your username")
    
    # Password Input
    password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
    
    # Forgot Password Link
    col1, col2 = st.columns([20, 10])
    with col2:
        if st.button("Forgot Password?", key="goto_forgot"):
            st.session_state.page = "otp_verification"
            st.rerun()

    # Login Button
    if st.button("LOG IN", key="login_button", use_container_width=True):
        if username and password:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, user_type FROM users WHERE username = ? AND password = ? AND user_type = ?", 
                (username, password, user_type.lower())
            )
            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state.user_id = user[0]
                st.session_state.logged_user = user[1]
                st.session_state.user_type = user[2]
                
                if user[2] == "admin":
                    st.session_state.page = "admin_dashboard"
                    st.success(f"Welcome Admin {user[1]}!")
                else:
                    st.session_state.page = "home"
                    st.success(f"Welcome {user[1]}!")
                
                st.rerun()
            else:
                st.error(f"Invalid credentials for {user_type} account")
        else:
            st.error("Please enter both username and password")
    
    # Sign Up Button
    if st.button("SIGN UP", key="signup_redirect", use_container_width=True):
        st.session_state.page = "signup"
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ========== SIGNUP PAGE ==========
elif st.session_state.page == "signup":
    show_header()
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown("### Create New Account")

    user_type = st.selectbox(
        "I am a...",
        ["Farmer", "Admin"],
        key="signup_user_type",
        help="Select your account type"
    )
    
    st.info(f"Creating a **{user_type}** account")

    username = st.text_input("Username", key="signup_username", placeholder="Choose a username")
    email = st.text_input("Email", key="signup_email", placeholder="your.email@example.com")
    phone = st.text_input("Phone Number", key="signup_phone", placeholder="+63 XXX XXX XXXX")
    password = st.text_input("Password", type="password", key="signup_password", placeholder="Create a strong password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password", placeholder="Re-enter your password")
   
    if st.button("Create Account", key="create_account"):
        if not all([username, email, phone, password, confirm_password]):
            st.error("Please fill in all fields")
        elif password != confirm_password:
            st.error("Passwords do not match")
        else:
            try:
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, email, phone, password, user_type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, email, phone, password, user_type.lower()))
                conn.commit()
                st.success(f"{user_type} account created successfully!")
                st.balloons()
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

# ========== ADMIN DASHBOARD ==========
elif st.session_state.page == "admin_dashboard":
    if st.session_state.user_type != "admin":
        st.error("Access Denied! Admin privileges required.")
        st.session_state.page = "home"
        st.rerun()
    
    
    st.markdown(f"""
        <div style='text-align: center; margin: 20px 0;'>
            <img src="https://cdn-icons-png.flaticon.com/128/3135/3135715.png" class="icon-medium">
            <h2>Admin Dashboard 
                <span class='user-type-badge badge-admin'>ADMIN</span>
            </h2>
            <p>Welcome, <strong>{st.session_state.logged_user}</strong></p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'farmer'")
    total_farmers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
    total_admins = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM history")
    total_detections = cursor.fetchone()[0]
    
    conn.close()
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <img src="https://cdn-icons-png.flaticon.com/128/2917/2917995.png" class="icon-medium">
                <div class="metric-value">{total_farmers}</div>
                <div class="metric-label">Total Farmers</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <img src="https://cdn-icons-png.flaticon.com/128/3135/3135715.png" class="icon-medium">
                <div class="metric-value">{total_admins}</div>
                <div class="metric-label">Total Admins</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <img src="https://cdn-icons-png.flaticon.com/128/2917/2917641.png" class="icon-medium">
                <div class="metric-value">{total_detections}</div>
                <div class="metric-label">Total Detections</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
        <div style='text-align: center;'>
            <img src="https://cdn-icons-png.flaticon.com/128/2920/2920277.png" class="icon-small">
            <strong style='font-size: 18px;'>System Management</strong>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Users", "Detection History", "Settings"])
    
    with tab1:
        st.write("**Registered Users**")
        conn = sqlite3.connect("users.db")
        users_df = pd.read_sql_query("SELECT id, username, email, user_type FROM users", conn)
        conn.close()
        st.dataframe(users_df, use_container_width=True)
    
    with tab2:
        st.write("**Recent Detection History**")
        conn = sqlite3.connect("users.db")
        history_df = pd.read_sql_query("""
            SELECT h.id, u.username, h.result, h.confidence, h.created_at 
            FROM history h 
            JOIN users u ON h.user_id = u.id 
            ORDER BY h.created_at DESC 
            LIMIT 50
        """, conn)
        conn.close()
        st.dataframe(history_df, use_container_width=True)
    
    with tab3:
        st.write("**System Settings**")
        st.info("Settings panel coming soon...")
    
    if st.button("Logout", key="admin_logout"):
        st.session_state.user_id = None
        st.session_state.logged_user = None
        st.session_state.user_type = None
        st.session_state.page = "login"
        st.rerun()


# ========== HOME SCREEN ==========
elif st.session_state.page == "home":
    st.markdown("""
    <style>
        /* Overall layout */
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

        .features-section { margin: 40px 0; }

        /* Tips section */
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

        /* Responsive tweaks */
        @media (max-width: 768px) {
            .feature-card {
                height: 150px;
                padding: 10px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # ===== HEADER =====
    st.markdown(
        f"""<div class="welcome-header">
            Welcome back, <span style="color: #4CAF50;">{st.session_state.logged_user}</span>!
            <div style="font-size: 15px; color: #6c757d; margin-top: 4px;">
                Ready to protect your palay today?
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    # ===== WEATHER FORECAST USING st.components.html =====
    import streamlit.components.v1 as components
    from datetime import datetime, timedelta

    CITY = "Manila,PH"

    def get_7day_forecast(city):
        today = datetime.now()
        temp_ranges = [
            {"max": 32, "min": 25, "icon": "01d"},
            {"max": 31, "min": 24, "icon": "02d"},
            {"max": 33, "min": 26, "icon": "03d"},
            {"max": 30, "min": 25, "icon": "10d"},
            {"max": 32, "min": 26, "icon": "01d"},
            {"max": 31, "min": 25, "icon": "02d"},
            {"max": 29, "min": 24, "icon": "04d"}
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

    if forecast:
        # Build complete HTML for weather section
        weather_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: white;
                    padding: 10px;
                    overflow-x: hidden;
                }}
                
                .weather-section {{
                    text-align: center;
                    margin-bottom: 20px;
                    width: 100%;
                }}

                .weather-header {{
                    font-size: 20px;
                    font-weight: 800;
                    color: #2e7d32;
                    margin-bottom: 10px;
                }}

                .weather-sub {{
                    font-size: 14px;
                    color: #555;
                    margin-bottom: 15px;
                }}

                .plantix-scroll {{
                    display: flex;
                    flex-direction: row;
                    flex-wrap: nowrap;
                    overflow-x: auto;
                    overflow-y: hidden;
                    gap: 12px;
                    padding: 10px 5px;
                    width: 100%;
                    scroll-behavior: smooth;
                    -webkit-overflow-scrolling: touch;
                    scroll-snap-type: x mandatory;
                }}

                .plantix-scroll::-webkit-scrollbar {{
                    height: 8px;
                }}
                
                .plantix-scroll::-webkit-scrollbar-thumb {{
                    background-color: #a5d6a7;
                    border-radius: 10px;
                }}
                
                .plantix-scroll::-webkit-scrollbar-track {{
                    background-color: #f0f0f0;
                    border-radius: 10px;
                }}

                .plantix-card {{
                    flex: 0 0 110px;
                    min-width: 110px;
                    max-width: 110px;
                    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                    border-radius: 16px;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.12);
                    text-align: center;
                    padding: 12px 8px;
                    transition: all 0.3s ease;
                    border: 1px solid #e8e8e8;
                    scroll-snap-align: start;
                }}

                .plantix-card:hover {{
                    transform: translateY(-4px);
                    box-shadow: 0 6px 15px rgba(76, 175, 80, 0.2);
                    border-color: #a5d6a7;
                }}

                .forecast-day {{
                    color: #2e7d32;
                    font-weight: 700;
                    font-size: 14px;
                    margin-bottom: 8px;
                }}

                .forecast-icon {{
                    width: 50px;
                    height: 50px;
                    margin: 8px auto;
                    display: block;
                }}

                .temp-container {{
                    margin-top: 8px;
                }}

                .temp-high {{ 
                    color: #ff7043; 
                    font-weight: bold; 
                    font-size: 13px; 
                }}
                
                .temp-low {{ 
                    color: #42a5f5; 
                    font-weight: bold; 
                    font-size: 13px; 
                }}
                
                .temp-separator {{
                    color: #999;
                    font-size: 13px;
                    margin: 0 3px;
                }}

                /* Desktop: Show 5-6 cards */
                @media (min-width: 769px) {{
                    .plantix-scroll {{
                        justify-content: center;
                    }}
                    .plantix-card {{
                        flex: 0 0 110px;
                    }}
                }}

                /* Tablet: Show 4-5 cards */
                @media (max-width: 768px) and (min-width: 481px) {{
                    .plantix-card {{
                        flex: 0 0 100px;
                        min-width: 100px;
                        max-width: 100px;
                        padding: 10px 6px;
                    }}
                    .forecast-icon {{
                        width: 45px;
                        height: 45px;
                    }}
                    .forecast-day {{
                        font-size: 13px;
                    }}
                    .temp-high, .temp-low {{
                        font-size: 12px;
                    }}
                }}

                /* Mobile: Show exactly 3 cards (rest need scroll) */
                @media (max-width: 480px) {{
                    .weather-header {{
                        font-size: 18px;
                    }}
                    .weather-sub {{
                        font-size: 13px;
                    }}
                    .plantix-scroll {{
                        gap: 10px;
                        padding: 10px 3px;
                    }}
                    .plantix-card {{
                        flex: 0 0 calc(33.333% - 7px);
                        min-width: calc(33.333% - 7px);
                        max-width: calc(33.333% - 7px);
                        padding: 10px 5px;
                    }}
                    .forecast-icon {{
                        width: 40px;
                        height: 40px;
                    }}
                    .forecast-day {{
                        font-size: 12px;
                    }}
                    .temp-high, .temp-low {{
                        font-size: 11px;
                    }}
                }}

                /* Extra small mobile: Show 3 cards more compactly */
                @media (max-width: 360px) {{
                    .plantix-card {{
                        flex: 0 0 calc(33.333% - 6px);
                        min-width: calc(33.333% - 6px);
                        max-width: calc(33.333% - 6px);
                        padding: 8px 4px;
                    }}
                    .forecast-icon {{
                        width: 35px;
                        height: 35px;
                    }}
                    .forecast-day {{
                        font-size: 11px;
                    }}
                    .temp-high, .temp-low {{
                        font-size: 10px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="weather-section">
                <div class="weather-header">🌦️ 7-Day Weather Forecast ({CITY})</div>
                <div class="weather-sub">Swipe left or right ➜</div>
                <div class="plantix-scroll">
        """
        
        # Add all weather cards
        for day in forecast:
            icon_url = f"https://openweathermap.org/img/wn/{day['icon']}@2x.png"
            weather_html += f"""
                    <div class='plantix-card'>
                        <div class='forecast-day'>{day['day_short']}</div>
                        <img class='forecast-icon' src='{icon_url}' alt='Weather Icon'>
                        <div class='temp-container'>
                            <span class='temp-high'>{day['temp_max']}°</span>
                            <span class='temp-separator'>/</span>
                            <span class='temp-low'>{day['temp_min']}°</span>
                        </div>
                    </div>
            """
        
        weather_html += """
                </div>
            </div>
        </body>
        </html>
        """
        
        # Render using components.html
        components.html(weather_html, height=220, scrolling=False)

    # ===== FEATURE BUTTONS =====
    st.markdown('<div class="features-section">', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown("""
        <div class="feature-card">
            <img src="https://cdn-icons-png.flaticon.com/128/1150/1150652.png" width="70">
            <div style="font-weight: bold; margin: 8px 0;">Detect Disease</div>
            <div style="font-size: 13px;">Upload images of palay plants</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Detect", key="detect_button", use_container_width=True):
            st.session_state.page = "detect"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="feature-card">
            <img src="https://cdn-icons-png.flaticon.com/128/12901/12901923.png" width="70">
            <div style="font-weight: bold; margin: 8px 0;">View History</div>
            <div style="font-size: 13px;">Check your previous scans</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View", key="history_button", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ===== TIPS SECTION =====
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

    show_bottom_nav('home')





# ========== OTP VERIFICATION PAGE ==========
elif st.session_state.page == "otp_verification":
    show_header()
    
    st.markdown("""
    <style>
    .otp-title {
        text-align: center;
        color: #2e7d32;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .otp-subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 14px;
        margin-bottom: 30px;
    }
    .timer-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin: 20px 0;
    }
    .timer-text {
        font-size: 36px;
        font-weight: bold;
        margin: 10px 0;
        letter-spacing: 2px;
    }
    .expired-box {
        background: linear-gradient(135deg, #f44336 0%, #e91e63 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin: 20px 0;
    }
    .email-sent-box {
        background: #e8f5e9;
        border-left: 5px solid #4CAF50;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

    if "otp_stage" not in st.session_state:
        st.session_state.otp_stage = "input_email"

    if st.session_state.otp_stage == "input_email":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/128/6195/6195699.png" width="80">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="otp-title">Forgot Password</div>', unsafe_allow_html=True)
        st.markdown('<div class="otp-subtitle">Enter your email to receive a verification code</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        input_email = st.text_input(
            "Email Address",
            key="otp_email_input",
            placeholder="your.email@gmail.com"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Send OTP", key="send_otp_btn", use_container_width=True, type="primary"):
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
                            st.error("Failed to send OTP. Please try again.")
                    else:
                        st.error("Email not found in our records.")
                else:
                    st.warning("Please enter your email address.")
        
        with col2:
            if st.button("Back to Login", key="back_to_login_from_forgot", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()

    elif st.session_state.otp_stage == "verify_otp":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/128/3143/3143609.png" width="80">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="otp-title">Verify OTP</div>', unsafe_allow_html=True)
        st.markdown('<div class="otp-subtitle">We sent a 6-digit code to your email</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="email-sent-box">
            <div style="margin-right: 15px;">
                <img src="https://cdn-icons-png.flaticon.com/128/732/732200.png" width="40">
            </div>
            <div>
                <strong style="color: #2e7d32;">OTP sent successfully!</strong><br>
                <span style="color: #6c757d; font-size: 13px;">Check your inbox: {st.session_state.otp_email}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        time_left = 180 - (time.time() - st.session_state.otp_start_time)
        
        if time_left > 0:
            minutes = int(time_left // 60)
            seconds = int(time_left % 60)
            st.markdown(f"""
            <div class="timer-box">
                <img src="https://cdn-icons-png.flaticon.com/128/2838/2838779.png" width="50" style="margin-bottom: 10px;">
                <div style="font-size: 14px; opacity: 0.9;">Time Remaining</div>
                <div class="timer-text">{minutes:02d}:{seconds:02d}</div>
                <div style="font-size: 14px; opacity: 0.9;">Code expires soon!</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="expired-box">
                <img src="https://cdn-icons-png.flaticon.com/128/3658/3658969.png" width="60" style="margin-bottom: 10px;">
                <div style="font-size: 20px; font-weight: bold;">OTP Expired</div>
                <div style="font-size: 14px; opacity: 0.9; margin-top: 5px;">Please request a new code</div>
            </div>
            """, unsafe_allow_html=True)

        entered_otp = st.text_input(
            "Enter 6-digit OTP",
            max_chars=6,
            placeholder="000000",
            key="otp_input"
        )
        
        submit_clicked = st.button("Submit OTP", key="verify_otp_btn", use_container_width=True, type="primary")
        
        if submit_clicked:
            if not entered_otp:
                st.error("Please enter the OTP code.")
            elif entered_otp == st.session_state.generated_otp and time_left > 0:
                st.success("OTP Verified Successfully!")
                st.session_state.page = "change_password"
                time.sleep(0.5)
                st.rerun()
            elif time_left <= 0:
                st.error("OTP has expired. Please request a new code.")
            else:
                st.error("Invalid OTP. Please check and try again.")

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        
        with col1:
            resend_clicked = st.button("Resend OTP", key="resend_otp_btn", use_container_width=True)
            if resend_clicked:
                now = time.time()
                if now - st.session_state.otp_start_time > 30:
                    new_otp = generate_otp()
                    st.session_state.generated_otp = new_otp
                    st.session_state.otp_start_time = now
                    sent = send_otp_email(st.session_state.otp_email, new_otp)
                    if sent:
                        st.success("New OTP sent to your email!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to resend OTP. Please try again.")
                else:
                    remaining_wait = 30 - (now - st.session_state.otp_start_time)
                    st.warning(f"Please wait {int(remaining_wait)} seconds before resending.")
        
        with col2:
            back_clicked = st.button("Change Email", key="back_to_email_btn", use_container_width=True)
            if back_clicked:
                st.session_state.otp_stage = "input_email"
                st.rerun()

        if time_left > 0 and not (submit_clicked or resend_clicked or back_clicked):
            time.sleep(1)
            st.rerun()

# ========== CHANGE PASSWORD PAGE ==========
elif st.session_state.page == "change_password":
    show_header()
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="https://cdn-icons-png.flaticon.com/128/2889/2889676.png" width="80">
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="otp-title">Create New Password</div>', unsafe_allow_html=True)
    st.markdown('<div class="otp-subtitle">Enter a strong password for your account</div>', unsafe_allow_html=True)
    
    st.info("Password must be at least 6 characters long")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    new_password = st.text_input(
        "New Password", 
        type="password", 
        key="new_password",
        placeholder="Enter new password"
    )
    
    confirm_password = st.text_input(
        "Confirm New Password", 
        type="password", 
        key="confirm_password",
        placeholder="Re-enter new password"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("Change Password", key="change_pwd_btn", type="primary", use_container_width=True):
            if not new_password or not confirm_password:
                st.error("Please fill in both password fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                try:
                    conn = sqlite3.connect("users.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password = ? WHERE email = ?", 
                                 (new_password, st.session_state.otp_email))
                    conn.commit()
                    conn.close()
                    
                    st.success("Password changed successfully!")
                    
                    for key in ['generated_otp', 'otp_start_time', 'otp_email', 'verified_user', 'otp_stage']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    time.sleep(1)
                    st.session_state.page = "login"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error changing password: {e}")
    
    with col2:
        if st.button("Cancel", key="back_to_login_from_pwd", use_container_width=True):
            for key in ['generated_otp', 'otp_start_time', 'otp_email', 'verified_user', 'otp_stage']:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.session_state.page = "login"
            st.rerun()
    
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding: 15px; background: #e8f5e9; border-radius: 10px;">
        <img src="https://cdn-icons-png.flaticon.com/128/190/190411.png" width="20" style="vertical-align: middle; margin-right: 8px;">
        <span style="color: #2e7d32; font-size: 13px;">
            <strong>Tip:</strong> Choose a password that's easy for you to remember but hard for others to guess.
        </span>
    </div>
    """, unsafe_allow_html=True)

# ========== ADMIN DASHBOARD ==========
elif st.session_state.page == "admin_dashboard":
    if st.session_state.user_type != "admin":
        st.error("Access Denied! Admin privileges required.")
        st.session_state.page = "home"
        st.rerun()
    
    show_header()
    
    st.markdown(f"""
        <div style='text-align: center; margin: 20px 0;'>
            <img src="https://cdn-icons-png.flaticon.com/128/3135/3135715.png" class="icon-medium">
            <h2>Admin Dashboard 
                <span class='user-type-badge badge-admin'>ADMIN</span>
            </h2>
            <p>Welcome, <strong>{st.session_state.logged_user}</strong></p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'farmer'")
    total_farmers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
    total_admins = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM history")
    total_detections = cursor.fetchone()[0]
    
    conn.close()
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <img src="https://cdn-icons-png.flaticon.com/128/1886/1886915.png" class="icon-medium">
                <div class="metric-value">{total_farmers}</div>
                <div class="metric-label">Total Farmers</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <img src="https://cdn-icons-png.flaticon.com/128/3135/3135715.png" class="icon-medium">
                <div class="metric-value">{total_admins}</div>
                <div class="metric-label">Total Admins</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <img src="https://cdn-icons-png.flaticon.com/128/18742/18742558.png" class="icon-medium">
                <div class="metric-value">{total_detections}</div>
                <div class="metric-label">Total Detections</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
        <div style='text-align: center;'>
            <img src="https://cdn-icons-png.flaticon.com/128/2920/2920277.png" class="icon-small">
            <strong style='font-size: 18px;'>System Management</strong>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Users", "Detection History", "Settings"])
    
    with tab1:
        st.write("**Registered Users**")
        conn = sqlite3.connect("users.db")
        users_df = pd.read_sql_query("SELECT id, username, email, user_type FROM users", conn)
        conn.close()
        st.dataframe(users_df, use_container_width=True)
    
    with tab2:
        st.write("**Recent Detection History**")
        conn = sqlite3.connect("users.db")
        history_df = pd.read_sql_query("""
            SELECT h.id, u.username, h.result, h.confidence, h.created_at 
            FROM history h 
            JOIN users u ON h.user_id = u.id 
            ORDER BY h.created_at DESC 
            LIMIT 50
        """, conn)
        conn.close()
        st.dataframe(history_df, use_container_width=True)
    
    with tab3:
        st.markdown("### System Settings")
        st.markdown("---")
        
        # ========== CHANGE ADMIN PASSWORD ==========
        st.markdown("#### Change Admin Password")
        
        col_pass1, col_pass2 = st.columns(2)
        
        with col_pass1:
            current_password = st.text_input("Current Password", type="password", key="current_pass")
            new_password = st.text_input("New Password", type="password", key="new_pass")
            confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pass")
            
            if st.button("Update Password", type="primary"):
                if not current_password or not new_password or not confirm_password:
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    conn = sqlite3.connect("users.db")
                    cursor = conn.cursor()
                    
                    # Verify current password
                    cursor.execute("SELECT password FROM users WHERE username = ? AND user_type = 'admin'", 
                                 (st.session_state.logged_user,))
                    result = cursor.fetchone()
                    
                    if result and result[0] == current_password:
                        cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
                                     (new_password, st.session_state.logged_user))
                        conn.commit()
                        st.success("Password updated successfully")
                    else:
                        st.error("Current password is incorrect")
                    
                    conn.close()
        
        with col_pass2:
            st.info("""
            **Password Requirements:**
            - Minimum 6 characters
            - Must match confirmation
            - Current password required for verification
            """)
        
        st.markdown("---")
        
        # ========== DELETE USER ACCOUNTS ==========
        st.markdown("#### Delete User Accounts")
        
        conn = sqlite3.connect("users.db")
        all_users_df = pd.read_sql_query("""
            SELECT id, username, email, user_type, created_at 
            FROM users 
            WHERE username != ?
            ORDER BY created_at DESC
        """, conn, params=(st.session_state.logged_user,))
        conn.close()
        
        if not all_users_df.empty:
            st.dataframe(all_users_df, use_container_width=True, hide_index=True)
            
            col_del1, col_del2 = st.columns([2, 1])
            
            with col_del1:
                user_id_to_delete = st.number_input(
                    "Enter User ID to Delete", 
                    min_value=1, 
                    step=1, 
                    key="delete_user_id"
                )
            
            with col_del2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Delete User", type="secondary"):
                    # Verify user exists and is not current admin
                    conn = sqlite3.connect("users.db")
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id_to_delete,))
                    user_result = cursor.fetchone()
                    
                    if not user_result:
                        st.error("User ID not found")
                    elif user_result[0] == st.session_state.logged_user:
                        st.error("Cannot delete your own account")
                    else:
                        # Delete user's history first
                        cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id_to_delete,))
                        
                        # Delete user
                        cursor.execute("DELETE FROM users WHERE id = ?", (user_id_to_delete,))
                        conn.commit()
                        st.success(f"User '{user_result[0]}' (ID: {user_id_to_delete}) deleted successfully")
                        st.rerun()
                    
                    conn.close()
        else:
            st.info("No other users in the system")
        
        st.markdown("---")
        
        # ========== EDIT USER ROLES ==========
        st.markdown("#### Edit User Roles")
        
        conn = sqlite3.connect("users.db")
        users_for_role_df = pd.read_sql_query("""
            SELECT id, username, email, user_type 
            FROM users 
            WHERE username != ?
            ORDER BY username
        """, conn, params=(st.session_state.logged_user,))
        conn.close()
        
        if not users_for_role_df.empty:
            col_role1, col_role2, col_role3 = st.columns([2, 2, 1])
            
            with col_role1:
                selected_user_id = st.selectbox(
                    "Select User",
                    users_for_role_df['id'].tolist(),
                    format_func=lambda x: f"{users_for_role_df[users_for_role_df['id']==x]['username'].values[0]} (ID: {x})",
                    key="role_user_select"
                )
            
            with col_role2:
                current_role = users_for_role_df[users_for_role_df['id']==selected_user_id]['user_type'].values[0]
                new_role = st.selectbox(
                    "Change Role To",
                    ["farmer", "admin"],
                    index=0 if current_role == "admin" else 1,
                    key="new_role_select"
                )
            
            with col_role3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Update Role", type="primary"):
                    if new_role == current_role:
                        st.warning("User already has this role")
                    else:
                        conn = sqlite3.connect("users.db")
                        cursor = conn.cursor()
                        
                        cursor.execute("UPDATE users SET user_type = ? WHERE id = ?", 
                                     (new_role, selected_user_id))
                        conn.commit()
                        conn.close()
                        
                        username = users_for_role_df[users_for_role_df['id']==selected_user_id]['username'].values[0]
                        st.success(f"User '{username}' role updated to '{new_role}'")
                        st.rerun()
            
            st.markdown(f"**Current Role:** {current_role.upper()}")
        else:
            st.info("No other users available for role modification")
        
        st.markdown("---")
        
        # ========== CONFIGURE DETECTION LIMITS ==========
        st.markdown("#### Configure Detection Limits")
        
        col_limit1, col_limit2 = st.columns(2)
        
        with col_limit1:
            history_display_limit = st.number_input(
                "Maximum History Logs Displayed",
                min_value=10,
                max_value=500,
                value=50,
                step=10,
                help="Set how many detection history records are shown in the dashboard"
            )
            
            max_records_per_user = st.number_input(
                "Maximum Records Per User",
                min_value=50,
                max_value=1000,
                value=200,
                step=50,
                help="Set storage limit for detection records per user"
            )
        
        with col_limit2:
            st.info(f"""
            **Current Configuration:**
            - Display Limit: {history_display_limit} records
            - Per User Limit: {max_records_per_user} records
            
            These settings control system performance and storage usage.
            """)
            
            if st.button("Apply Configuration"):
                st.success("Configuration settings updated successfully")
        
        st.markdown("---")
        
        # ========== SYSTEM SUMMARY ==========
        st.markdown("#### System Summary")
        
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'farmer'")
        total_farmers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
        total_admins = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM history")
        total_detections = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Get recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM history 
            WHERE DATE(created_at) = DATE('now')
        """)
        today_detections = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM history 
            WHERE DATE(created_at) >= DATE('now', '-7 days')
        """)
        week_detections = cursor.fetchone()[0]
        
        conn.close()
        
        col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
        
        with col_sum1:
            st.metric("Total Users", total_users)
            st.caption(f"Farmers: {total_farmers} | Admins: {total_admins}")
        
        with col_sum2:
            st.metric("Total Detections", total_detections)
        
        with col_sum3:
            st.metric("Today's Detections", today_detections)
        
        with col_sum4:
            st.metric("This Week", week_detections)
        
        st.markdown("---")
        
        # ========== ABOUT SYSTEM ==========
        st.markdown("#### About System")
        
        st.markdown("""
        **Palay Protector v1.0**
        
        Palay Protector is an intelligent rice disease detection system designed to help farmers 
        identify and manage crop diseases efficiently. The system uses advanced machine learning 
        algorithms to analyze rice plant images and provide accurate disease classifications.
        
        **Key Features:**
        - Real-time disease detection and classification
        - Comprehensive detection history tracking
        - Multi-user support with role-based access control
        - Administrative dashboard for system management
        - Secure user authentication and data management
        
        **System Specifications:**
        - Database: SQLite
        - Framework: Streamlit
        - Version: 1.0
        - Supported Diseases: Multiple rice disease classifications
        
        **Administrator Capabilities:**
        - User management and role assignment
        - System configuration and monitoring
        - Detection history oversight
        - Security and access control
        
        **Support:**
        For technical support or inquiries, please contact your system administrator.
        
        ---
        *Palay Protector - Protecting Rice Crops Through Technology*
        """)
        
        # Database Information
        import os
        db_size = os.path.getsize("users.db") / 1024  # Size in KB
        
        col_about1, col_about2 = st.columns(2)
        
        with col_about1:
            st.markdown(f"""
            **Database Information:**
            - File: users.db
            - Size: {db_size:.2f} KB
            - Tables: users, history
            """)
        
        with col_about2:
            st.markdown("""
            **Last System Update:**
            - Version: 1.0
            - Release Date: 2024
            - Status: Active
            """)
    
    if st.button("Logout", key="admin_logout"):
        st.session_state.user_id = None
        st.session_state.logged_user = None
        st.session_state.user_type = None
        st.session_state.page = "login"
        st.rerun()

# ========== HOME PAGE ==========
elif st.session_state.page == "home":
    if st.session_state.user_type == "admin":
        st.warning("You are logged in as Admin. Redirecting to Admin Dashboard...")
        st.session_state.page = "admin_dashboard"
        st.rerun()
    
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
        .weather-section {
            margin-bottom: 40px;
        }
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
        .forecast-box {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            min-width: 90px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
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
        }
        .forecast-temp {
            font-size: 13px;
            font-weight: bold;
            color: #333;
        }
        .temp-high { color: #ff5722; }
        .temp-low { color: #2196f3; }
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
        }
        .tips-text {
            font-size: 14px;
            color: #555;
            line-height: 1.5;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        f"""<div class="welcome-header">
            Welcome back, <span style="color: #4CAF50;">{st.session_state.logged_user}</span>!
            <div style="font-size: 15px; color: #6c757d; margin-top: 4px;">
                Ready to protect your palay today?
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    from datetime import datetime, timedelta

    CITY = "Manila,PH"

    def get_7day_forecast(city):
        today = datetime.now()
        temp_ranges = [
            {"max": 32, "min": 25, "icon": "01d"},
            {"max": 31, "min": 24, "icon": "02d"},
            {"max": 33, "min": 26, "icon": "03d"},
            {"max": 30, "min": 25, "icon": "10d"},
            {"max": 32, "min": 26, "icon": "01d"},
            {"max": 31, "min": 25, "icon": "02d"},
            {"max": 29, "min": 24, "icon": "04d"}
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

    if forecast:
        st.markdown('<div class="weather-section">', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="weather-header">Weather Forecast ({CITY})</div>
        """, unsafe_allow_html=True)
        
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
        if st.button("Detect", key="detect_button", use_container_width=True):
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
        if st.button("View", key="history_button", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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

    show_bottom_nav('home')

# ========== OTP VERIFICATION PAGE ==========
elif st.session_state.page == "otp_verification":
    show_header()
    
    st.markdown("""
    <style>
    .otp-title {
        text-align: center;
        color: #2e7d32;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .otp-subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 14px;
        margin-bottom: 30px;
    }
    .timer-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin: 20px 0;
    }
    .timer-text {
        font-size: 36px;
        font-weight: bold;
        margin: 10px 0;
        letter-spacing: 2px;
    }
    .expired-box {
        background: linear-gradient(135deg, #f44336 0%, #e91e63 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin: 20px 0;
    }
    .email-sent-box {
        background: #e8f5e9;
        border-left: 5px solid #4CAF50;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

    if "otp_stage" not in st.session_state:
        st.session_state.otp_stage = "input_email"

    if st.session_state.otp_stage == "input_email":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/128/6195/6195699.png" width="80">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="otp-title">Forgot Password</div>', unsafe_allow_html=True)
        st.markdown('<div class="otp-subtitle">Enter your email to receive a verification code</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        input_email = st.text_input(
            "Email Address",
            key="otp_email_input",
            placeholder="your.email@gmail.com"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Send OTP", key="send_otp_btn", use_container_width=True, type="primary"):
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
                            st.error("Failed to send OTP. Please try again.")
                    else:
                        st.error("Email not found in our records.")
                else:
                    st.warning("Please enter your email address.")
        
        with col2:
            if st.button("Back to Login", key="back_to_login_from_forgot", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()

    elif st.session_state.otp_stage == "verify_otp":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/128/3143/3143609.png" width="80">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="otp-title">Verify OTP</div>', unsafe_allow_html=True)
        st.markdown('<div class="otp-subtitle">We sent a 6-digit code to your email</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="email-sent-box">
            <div style="margin-right: 15px;">
                <img src="https://cdn-icons-png.flaticon.com/128/732/732200.png" width="40">
            </div>
            <div>
                <strong style="color: #2e7d32;">OTP sent successfully!</strong><br>
                <span style="color: #6c757d; font-size: 13px;">Check your inbox: {st.session_state.otp_email}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        time_left = 180 - (time.time() - st.session_state.otp_start_time)
        
        if time_left > 0:
            minutes = int(time_left // 60)
            seconds = int(time_left % 60)
            st.markdown(f"""
            <div class="timer-box">
                <img src="https://cdn-icons-png.flaticon.com/128/2838/2838779.png" width="50" style="margin-bottom: 10px;">
                <div style="font-size: 14px; opacity: 0.9;">Time Remaining</div>
                <div class="timer-text">{minutes:02d}:{seconds:02d}</div>
                <div style="font-size: 14px; opacity: 0.9;">Code expires soon!</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="expired-box">
                <img src="https://cdn-icons-png.flaticon.com/128/3658/3658969.png" width="60" style="margin-bottom: 10px;">
                <div style="font-size: 20px; font-weight: bold;">OTP Expired</div>
                <div style="font-size: 14px; opacity: 0.9; margin-top: 5px;">Please request a new code</div>
            </div>
            """, unsafe_allow_html=True)

        entered_otp = st.text_input(
            "Enter 6-digit OTP",
            max_chars=6,
            placeholder="000000",
            key="otp_input"
        )
        
        submit_clicked = st.button("Submit OTP", key="verify_otp_btn", use_container_width=True, type="primary")
        
        if submit_clicked:
            if not entered_otp:
                st.error("Please enter the OTP code.")
            elif entered_otp == st.session_state.generated_otp and time_left > 0:
                st.success("OTP Verified Successfully!")
                st.session_state.page = "change_password"
                time.sleep(0.5)
                st.rerun()
            elif time_left <= 0:
                st.error("OTP has expired. Please request a new code.")
            else:
                st.error("Invalid OTP. Please check and try again.")

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        
        with col1:
            resend_clicked = st.button("Resend OTP", key="resend_otp_btn", use_container_width=True)
            if resend_clicked:
                now = time.time()
                if now - st.session_state.otp_start_time > 30:
                    new_otp = generate_otp()
                    st.session_state.generated_otp = new_otp
                    st.session_state.otp_start_time = now
                    sent = send_otp_email(st.session_state.otp_email, new_otp)
                    if sent:
                        st.success("New OTP sent to your email!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to resend OTP. Please try again.")
                else:
                    remaining_wait = 30 - (now - st.session_state.otp_start_time)
                    st.warning(f"Please wait {int(remaining_wait)} seconds before resending.")
        
        with col2:
            back_clicked = st.button("Change Email", key="back_to_email_btn", use_container_width=True)
            if back_clicked:
                st.session_state.otp_stage = "input_email"
                st.rerun()

        if time_left > 0 and not (submit_clicked or resend_clicked or back_clicked):
            time.sleep(1)
            st.rerun()

# ========== CHANGE PASSWORD PAGE ==========
elif st.session_state.page == "change_password":
    show_header()
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="https://cdn-icons-png.flaticon.com/128/2889/2889676.png" width="80">
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="otp-title">Create New Password</div>', unsafe_allow_html=True)
    st.markdown('<div class="otp-subtitle">Enter a strong password for your account</div>', unsafe_allow_html=True)
    
    st.info("Password must be at least 6 characters long")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    new_password = st.text_input(
        "New Password", 
        type="password", 
        key="new_password",
        placeholder="Enter new password"
    )
    
    confirm_password = st.text_input(
        "Confirm New Password", 
        type="password", 
        key="confirm_password",
        placeholder="Re-enter new password"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("Change Password", key="change_pwd_btn", type="primary", use_container_width=True):
            if not new_password or not confirm_password:
                st.error("Please fill in both password fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                try:
                    conn = sqlite3.connect("users.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password = ? WHERE email = ?", 
                                 (new_password, st.session_state.otp_email))
                    conn.commit()
                    conn.close()
                    
                    st.success("Password changed successfully!")
                    
                    for key in ['generated_otp', 'otp_start_time', 'otp_email', 'verified_user', 'otp_stage']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    time.sleep(1)
                    st.session_state.page = "login"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error changing password: {e}")
    
    with col2:
        if st.button("Cancel", key="back_to_login_from_pwd", use_container_width=True):
            for key in ['generated_otp', 'otp_start_time', 'otp_email', 'verified_user', 'otp_stage']:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.session_state.page = "login"
            st.rerun()
    
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding: 15px; background: #e8f5e9; border-radius: 10px;">
        <img src="https://cdn-icons-png.flaticon.com/128/190/190411.png" width="20" style="vertical-align: middle; margin-right: 8px;">
        <span style="color: #2e7d32; font-size: 13px;">
            <strong>Tip:</strong> Choose a password that's easy for you to remember but hard for others to guess.
        </span>
    </div>
    """, unsafe_allow_html=True)

# ========== HOME SCREEN ==========
elif st.session_state.page == "home":
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
        .weather-section {
            margin-bottom: 40px;
        }
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



    st.markdown(
        f"""<div class="welcome-header">
            Welcome back, <span style="color: #4CAF50;">{st.session_state.logged_user}</span>!
            <div style="font-size: 15px; color: #6c757d; margin-top: 4px;">
                Ready to protect your palay today?
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    from datetime import datetime, timedelta

    CITY = "Manila,PH"

    def get_7day_forecast(city):
        today = datetime.now()
        temp_ranges = [
            {"max": 32, "min": 25, "icon": "01d"},
            {"max": 31, "min": 24, "icon": "02d"},
            {"max": 33, "min": 26, "icon": "03d"},
            {"max": 30, "min": 25, "icon": "10d"},
            {"max": 32, "min": 26, "icon": "01d"},
            {"max": 31, "min": 25, "icon": "02d"},
            {"max": 29, "min": 24, "icon": "04d"}
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

    if forecast:
        st.markdown('<div class="weather-section">', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="weather-header">🌤️ 7-Day Weather Forecast ({CITY})</div>
        """, unsafe_allow_html=True)
        
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
        if st.button("Detect", key="detect_button", use_container_width=True):
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
        if st.button("View", key="history_button", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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

    show_bottom_nav('home')

# ========== ENHANCED DETECTION SCREEN WITH CAMERA ==========
elif st.session_state.page == "detect":
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
            .upload-option-box {
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                margin: 10px;
            }
            .upload-option-box:hover {
                border-color: #4CAF50;
                box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
                transform: translateY(-2px);
            }
        </style>
    """, unsafe_allow_html=True)

    
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='color: #2e7d32;'>Disease Detection</h2>
        <p style='color: #6c757d;'>Upload rice leaf image for analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"], key="file_upload")
    
    st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
    
    # Camera input
    camera_photo = st.camera_input("Take a picture", key="camera_input")
    
    # Determine which image to use
    image_to_use = None
    image_source = None
    
    if uploaded_file is not None:
        image_to_use = uploaded_file
        image_source = "upload"
    elif camera_photo is not None:
        image_to_use = camera_photo
        image_source = "camera"

    # Display preview
    if image_to_use is not None:
        image = Image.open(image_to_use)
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        st.markdown(f"""
        <div class="upload-section">
            <img src="https://cdn-icons-png.flaticon.com/128/2659/2659360.png" width="50" style="margin-bottom: 15px;">
            <div class="upload-text">Image Preview</div>
            <div class="upload-subtext">Ready for analysis</div>
            <img src="data:image/png;base64,{img_str}" class="preview-image" width="300">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="upload-section">
            <img src="https://cdn-icons-png.flaticon.com/128/1829/1829589.png" width="60" style="margin-bottom: 15px;">
            <div class="upload-text">Upload Rice Leaf Image</div>
            <div class="upload-subtext">Browse files or take a photo to get started</div>
        </div>
        """, unsafe_allow_html=True)
 
    # Detect button
    if st.button("DETECT DISEASE", key="detect_btn", use_container_width=True, type="primary"):
        if image_to_use is None:
            st.error("Please upload an image or take a photo first.")
        else:
            with st.spinner("Analyzing image..."):
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        image.save(tmp_file, format="JPEG")
                        tmp_file_path = tmp_file.name
                    
                    client = init_client()
                    result = client.infer(tmp_file_path, model_id="palayprotector-project/1")
                    
                    if result.get("predictions"):
                        for pred in result["predictions"]:
                            disease = pred["class"]
                            confidence = pred["confidence"] * 100
                            
                            st.markdown(f"""
                            <div class='result-box disease-result'>
                                <h2 style="margin: 0 0 15px 0; color: #2e7d32;">Detection Result</h2>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                    <span style="font-weight: bold; color: #d32f2f; font-size: 28px;">{disease}</span>
                                    <span style="font-weight: bold; color: #2e7d32; font-size: 24px;">{confidence:.1f}%</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {confidence}%;"></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
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
                            <h2 style="margin: 0 0 15px 0; color: #2e7d32;">Detection Result</h2>
                            <div style="text-align: center; padding: 20px;">
                                <img src="https://cdn-icons-png.flaticon.com/128/5610/5610944.png" width="60">
                                <h2 style="color: #2e7d32; font-size: 28px; margin: 15px 0;">Healthy Rice Plant</h2>
                                <p style="font-size: 16px;">No diseases detected</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error during detection: {str(e)}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    

    show_bottom_nav('detect')

# ========== HISTORY SCREEN ==========
elif st.session_state.page == "history":
    

    st.markdown("""
    <div style="background:#e8f5e9; color:#1b5e20; 
                padding:10px; border-radius:8px; 
                text-align:center; margin-bottom:15px;">
        <h3 style="margin:0; font-size:30px;">Detection History</h3>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.user_id is None:
        st.warning("⚠ Please log in to view your history.")
    else:
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

            st.components.v1.html(table_html, height=400, scrolling=True)

        else:
            st.info("No history records yet.")

    show_bottom_nav('history')

# ========== DISEASE LIBRARY ==========
elif st.session_state.page == "library":
    
    
    # Custom CSS for Library Page
    st.markdown("""
    <style>
    .library-header {
        text-align: center;
        color: #2e7d32;
        margin-bottom: 20px;
    }
    .search-container {
        margin: 20px 0;
    }
    .disease-card {
        background: white;
        border-left: 5px solid #4CAF50;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .disease-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .disease-title {
        font-size: 20px;
        font-weight: bold;
        color: #1b5e20;
        margin-bottom: 5px;
    }
    .disease-scientific {
        font-style: italic;
        color: #6c757d;
        font-size: 14px;
        margin-bottom: 10px;
    }
    .severity-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .severity-high {
        background-color: #ffebee;
        color: #c62828;
    }
    .severity-medium {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .severity-low {
        background-color: #e8f5e9;
        color: #2e7d32;
    }
    .info-section {
        margin: 15px 0;
    }
    .info-title {
        font-weight: bold;
        color: #2e7d32;
        font-size: 15px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
    }
    .info-content {
        color: #424242;
        line-height: 1.6;
        font-size: 14px;
        padding-left: 10px;
    }
    .tip-box {
        background: #e8f5e9;
        border-left: 4px solid #4CAF50;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="library-header">
        <h2>Rice Disease Library</h2>
        <p style="color: #6c757d;">Complete guide to rice plant diseases</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Search functionality
    search = st.text_input("Search diseases...", key="disease_search", placeholder="Type disease name...")
    
    # Enhanced disease database with detailed information - ALL 18 DISEASES
    diseases = [
        {
            "name": "Brown Spot",
            "scientific": "Bipolaris oryzae",
            "severity": "Medium",
            "description": "A fungal disease common in nutrient-deficient fields, particularly those lacking potassium.",
            "symptoms": [
                "Small circular brown spots on leaves",
                "Spots have yellow halos",
                "Affects both leaves and grains",
                "Reduces grain quality and weight"
            ],
            "treatment": [
                "Apply mancozeb or copper fungicides",
                "Improve soil nutrition (especially potassium)",
                "Remove infected plant parts",
                "Ensure proper drainage"
            ],
            "prevention": [
                "Maintain balanced soil nutrition",
                "Use healthy certified seeds",
                "Practice proper water management",
                "Avoid stress conditions"
            ],
            "image": "https://apps.lucidcentral.org/ppp_v9/images/entities/rice_brown_leaf_spot_427/5390490lgpt.jpg"
        },
        {
            "name": "Sheath Blight",
            "scientific": "Rhizoctonia solani",
            "severity": "High",
            "description": "A major fungal disease that thrives in warm, humid conditions with dense plant populations.",
            "symptoms": [
                "Oval or irregular lesions on leaf sheaths",
                "Greenish-gray lesions with brown borders",
                "Lesions merge and spread upward",
                "Plant lodging in severe cases"
            ],
            "treatment": [
                "Apply validamycin or hexaconazole fungicides",
                "Remove infected plant debris after harvest",
                "Improve air circulation in the field",
                "Reduce plant density"
            ],
            "prevention": [
                "Use proper plant spacing",
                "Avoid excessive nitrogen fertilization",
                "Drain fields periodically",
                "Practice crop rotation with non-host crops"
            ],
            "image": "https://th.bing.com/th/id/R.74ee4c2cbd251001c04c8b984b754cf0?rik=x%2bM1DIRpKy7dQw&riu=http%3a%2f%2f2.bp.blogspot.com%2f_-rGxVjqS77w%2fSsQ7mTG2bnI%2fAAAAAAAAAaY%2fGEv3UJtn7eE%2fw1200-h630-p-k-no-nu%2fSHEATH%2bBLIGHT.jpg&ehk=syWAczjiAoUbiwqvNeQOi48XNm3JzXEqpGJ4wCIym8U%3d&risl=&pid=ImgRaw&r=0"
        },
        {
            "name": "Bacterial Leaf Blight",
            "scientific": "Xanthomonas oryzae pv. oryzae",
            "severity": "High",
            "description": "A serious bacterial disease that affects rice plants at all growth stages, especially during rainy seasons.",
            "symptoms": [
                "Water-soaked lesions on leaf tips and edges",
                "Yellowing of infected leaves",
                "Wilting of seedlings (kresek symptom)",
                "White bacterial ooze on leaves"
            ],
            "treatment": [
                "Apply copper-based bactericides",
                "Remove and destroy infected plants",
                "Improve field drainage",
                "Use certified disease-free seeds"
            ],
            "prevention": [
                "Plant resistant varieties",
                "Avoid injury to plants",
                "Balance nitrogen fertilization",
                "Maintain proper spacing for air circulation"
            ],
            "image": "https://toagriculture.com/wp-content/uploads/2022/12/Bacterial-blight-disease-of-rice-Soci.jpg"
        },
        {
            "name": "Healthy Rice",
            "scientific": "Oryza sativa (Healthy)",
            "severity": "Low",
            "description": "Healthy rice plants showing normal growth and development without any disease symptoms.",
            "symptoms": [
                "Vibrant green leaves",
                "Uniform growth pattern",
                "No lesions or discoloration",
                "Strong and upright stems"
            ],
            "treatment": [
                "No treatment needed",
                "Continue good agricultural practices",
                "Monitor regularly for early disease detection",
                "Maintain preventive measures"
            ],
            "prevention": [
                "Use certified quality seeds",
                "Practice integrated pest management",
                "Maintain balanced nutrition",
                "Ensure proper water management"
            ],
            "image": "https://thumbs.dreamstime.com/b/close-up-rice-plant-leaves-dew-drops-190913252.jpg"
        },
        {
            "name": "Rice Hispa",
            "scientific": "Dicladispa armigera",
            "severity": "Medium",
            "description": "A pest infestation causing white streaks on leaves due to larvae feeding between leaf surfaces.",
            "symptoms": [
                "White longitudinal streaks on leaves",
                "Parallel feeding marks",
                "Dried and papery leaf appearance",
                "Reduced photosynthesis"
            ],
            "treatment": [
                "Apply appropriate insecticides",
                "Remove heavily infested leaves",
                "Flood the field to kill pupae",
                "Use light traps for adults"
            ],
            "prevention": [
                "Avoid close plant spacing",
                "Remove weeds around fields",
                "Use hispa-resistant varieties",
                "Practice proper field sanitation"
            ],
            "image": "https://wordpress-cdn-echoupaladvisory.echoupal.co.in/wp-content/uploads/2022/03/ricehipsa2-1.jpg"
        },
        {
            "name": "False Smut",
            "scientific": "Ustilaginoidea virens",
            "severity": "Medium",
            "description": "A fungal disease affecting rice grains, forming large greenish-black spore balls on panicles.",
            "symptoms": [
                "Greenish-black velvety balls on grains",
                "Individual grains enlarged",
                "Powder-covered spore balls",
                "Reduced grain quality"
            ],
            "treatment": [
                "Apply fungicides during flowering",
                "Remove and burn infected panicles",
                "Improve field drainage",
                "Reduce humidity in field"
            ],
            "prevention": [
                "Use resistant varieties",
                "Avoid excessive nitrogen fertilization",
                "Maintain proper plant spacing",
                "Practice crop rotation"
            ],
            "image": "https://tse2.mm.bing.net/th/id/OIP.TZd75GWVA5aL_qxqLemfMAHaFj?cb=12&rs=1&pid=ImgDetMain&o=7&rm=3"
        },
        {
            "name": "Leaf Smut",
            "scientific": "Entyloma oryzae",
            "severity": "Low",
            "description": "A minor fungal disease causing small black angular spots on leaves.",
            "symptoms": [
                "Small angular black spots on leaves",
                "Spots scattered on leaf surface",
                "Minimal yield impact",
                "More common in wet conditions"
            ],
            "treatment": [
                "Usually no treatment needed",
                "Improve field drainage if severe",
                "Reduce leaf wetness duration",
                "Apply fungicides if widespread"
            ],
            "prevention": [
                "Use quality seeds",
                "Maintain proper field drainage",
                "Avoid overhead irrigation",
                "Practice balanced fertilization"
            ],
            "image": "https://bugwoodcloud.org/images/768x512/5390514.jpg"
        },
        {
            "name": "Leaf Scald",
            "scientific": "Monographella albescens",
            "severity": "Medium",
            "description": "A fungal disease causing distinctive banded lesions on rice leaves.",
            "symptoms": [
                "Alternating light and dark bands on leaves",
                "Lesions start from leaf tips",
                "Yellowing of affected areas",
                "Premature leaf drying"
            ],
            "treatment": [
                "Apply appropriate fungicides",
                "Remove infected plant debris",
                "Improve air circulation",
                "Ensure proper drainage"
            ],
            "prevention": [
                "Use resistant varieties",
                "Avoid excessive nitrogen",
                "Practice proper spacing",
                "Maintain field sanitation"
            ],
            "image": "https://bugwoodcloud.org/images/768x512/5390511.jpg"
        },
        {
            "name": "Narrow Brown Leaf Spot",
            "scientific": "Cercospora janseana",
            "severity": "Low",
            "description": "A minor leaf spot disease causing narrow brown lesions on rice leaves.",
            "symptoms": [
                "Narrow brown linear lesions",
                "Lesions parallel to leaf veins",
                "Yellow halos around spots",
                "Minimal impact on yield"
            ],
            "treatment": [
                "Usually no treatment required",
                "Apply fungicides if severe",
                "Remove heavily infected leaves",
                "Improve field conditions"
            ],
            "prevention": [
                "Use healthy seeds",
                "Maintain balanced nutrition",
                "Ensure proper drainage",
                "Practice crop rotation"
            ],
            "image": "https://tse1.mm.bing.net/th/id/OIP.YeSPfVgbqHLbF54KLRtl9gHaE9?cb=12&rs=1&pid=ImgDetMain&o=7&rm=3"
        },
        {
            "name": "Rice Blast",
            "scientific": "Pyricularia oryzae",
            "severity": "High",
            "description": "Rice blast is one of the most destructive diseases of rice, causing significant yield losses worldwide.",
            "symptoms": [
                "Diamond-shaped lesions on leaves",
                "White to gray centers with brown margins",
                "Lesions on leaf nodes and panicles",
                "Neck rot in severe cases"
            ],
            "treatment": [
                "Apply fungicides containing tricyclazole or azoxystrobin",
                "Remove infected plant debris",
                "Maintain proper field drainage",
                "Use resistant varieties"
            ],
            "prevention": [
                "Use resistant varieties",
                "Avoid excessive nitrogen fertilization",
                "Maintain proper water management",
                "Practice crop rotation"
            ],
            "image": "https://tse2.mm.bing.net/th/id/OIP.N5zA4MwJYeI20Q2YGCme2wHaE9?cb=12&rs=1&pid=ImgDetMain&o=7&rm=3"
        },
        {
            "name": "Rice Stripes",
            "scientific": "Rice stripe virus (RSV)",
            "severity": "High",
            "description": "A viral disease transmitted by small brown planthoppers causing chlorotic stripes on leaves.",
            "symptoms": [
                "Yellow or chlorotic stripes on leaves",
                "Stunted plant growth",
                "Reduced tillering",
                "Incomplete panicle exertion"
            ],
            "treatment": [
                "Remove infected plants immediately",
                "Control planthopper vectors",
                "No direct cure for viral infection",
                "Use resistant varieties"
            ],
            "prevention": [
                "Plant virus-resistant varieties",
                "Control planthopper populations",
                "Adjust planting dates",
                "Remove volunteer rice plants"
            ],
            "image": "https://tse2.mm.bing.net/th/id/OIP.hPJMjM6glnzy2itgSj9H6QHaE8?cb=12&w=1500&h=1000&rs=1&pid=ImgDetMain&o=7&rm=3"
        },
        {
            "name": "Rice Tungro",
            "scientific": "Rice tungro bacilliform virus (RTBV) & Rice tungro spherical virus (RTSV)",
            "severity": "High",
            "description": "A viral disease transmitted by green leafhopper, causing severe stunting and yield loss.",
            "symptoms": [
                "Yellow or orange-yellow leaf discoloration",
                "Stunted plant growth",
                "Reduced number of tillers",
                "Incomplete panicle formation"
            ],
            "treatment": [
                "Remove and destroy infected plants immediately",
                "Control leafhopper vectors with insecticides",
                "No direct cure available for viral infection",
                "Replant with resistant varieties if severe"
            ],
            "prevention": [
                "Plant tungro-resistant varieties",
                "Control green leafhopper populations",
                "Adjust planting dates to avoid peak vector activity",
                "Remove weeds that host leafhoppers"
            ],
            "image": "https://tse1.mm.bing.net/th/id/OIP.rtDAwQ8P15ghoq0nTNZu3gHaFj?cb=12&rs=1&pid=ImgDetMain&o=7&rm=3"
        }
    ]
    
    # Filter diseases based on search
    filtered_diseases = diseases
    if search and search.strip():  # Check if search has actual text
        search_lower = search.lower().strip()
        filtered_diseases = [
            d for d in diseases 
            if search_lower in d['name'].lower() or search_lower in d['scientific'].lower()
        ]
    
    # Display filtered diseases
    if filtered_diseases:
        for disease in filtered_diseases:
            with st.expander(f"**{disease['name']}** - *{disease['scientific']}*", expanded=False):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.image(disease['image'], width=150)
                
                with col2:
                    # Severity badge
                    severity_class = f"severity-{disease['severity'].lower()}"
                    st.markdown(f"""
                    <div class="{severity_class}" style="display: inline-block; padding: 4px 12px; border-radius: 15px; font-size: 12px; font-weight: bold;">
                        Severity: {disease['severity']}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Description
                st.markdown(f"<p style='margin: 15px 0; color: #424242;'>{disease['description']}</p>", unsafe_allow_html=True)
                
                # Symptoms
                st.markdown("""
                <div class="info-title">
                    <img src="https://cdn-icons-png.flaticon.com/128/2755/2755944.png" width="20" style="margin-right: 8px;">
                    Symptoms
                </div>
                """, unsafe_allow_html=True)
                for symptom in disease['symptoms']:
                    st.markdown(f"• {symptom}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Treatment
                st.markdown("""
                <div class="info-title">
                    <img src="https://cdn-icons-png.flaticon.com/128/17085/17085104.png" width="20" style="margin-right: 8px;">
                    Treatment
                </div>
                """, unsafe_allow_html=True)
                for treatment in disease['treatment']:
                    st.markdown(f"• {treatment}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Prevention
                st.markdown("""
                <div class="info-title">
                    <img src="https://cdn-icons-png.flaticon.com/128/3774/3774299.png" width="20" style="margin-right: 8px;">
                    Prevention
                </div>
                """, unsafe_allow_html=True)
                for prevention in disease['prevention']:
                    st.markdown(f"• {prevention}")
    else:
        st.info("No diseases found matching your search.")
    
    # Tips section at bottom
    st.markdown("""
    <div class="tip-box">
        <div style="font-weight: bold; color: #2e7d32; margin-bottom: 8px;">
            💡 Pro Tips for Disease Management
        </div>
        <div style="font-size: 14px; color: #424242;">
            • Regular monitoring is key to early detection<br>
            • Always use certified disease-free seeds<br>
            • Maintain proper field sanitation<br>
            • Rotate crops to break disease cycles<br>
            • Consult agricultural extension services for severe cases
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    show_bottom_nav('library')


# ========== ENHANCED PROFILE PAGE ==========
elif st.session_state.page == "profile":
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .profile-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin-bottom: 2rem;
    }
    .profile-avatar {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: white;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #667eea;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    .metric-label {
        color: #6c757d;
        font-size: 0.9rem;
    }
    .info-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # FLATICON LINKS - PALITAN MO LANG YUNG MGA ITO!
    profile_image = "https://cdn-icons-png.flaticon.com/512/2202/2202112.png"
    stats_icon = "https://cdn-icons-png.flaticon.com/512/2936/2936886.png"
    healthy_icon = "https://cdn-icons-png.flaticon.com/512/5610/5610944.png"
    disease_icon = "https://cdn-icons-png.flaticon.com/512/564/564619.png"
    accuracy_icon = "https://cdn-icons-png.flaticon.com/512/1828/1828640.png"
    
    # Profile Header Card
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">
            <img src="{profile_image}" style="width: 80px; height: 80px; border-radius: 50%;">
        </div>
        <h2 style="margin: 0;">{st.session_state.logged_user}</h2>
        <p style="opacity: 0.9; margin: 0.5rem 0;">farmer@palayprotector.com</p>
        <p style="opacity: 0.8; font-size: 0.9rem;">Member since October 2025</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistics Section
    st.markdown("### Activity Statistics")
    
    # GET REAL DATA FROM DATABASE - DYNAMIC FROM HISTORY TABLE!
    total_scans = 0
    healthy_count = 0
    detected_count = 0
    
    try:
        # Connect to users.db (your actual database)
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Query to get user statistics from HISTORY table
        cursor.execute("""
            SELECT 
                COUNT(*) as total_scans,
                SUM(CASE WHEN result = 'Healthy' THEN 1 ELSE 0 END) as healthy_count,
                SUM(CASE WHEN result != 'Healthy' THEN 1 ELSE 0 END) as detected_count
            FROM history
            WHERE user_id = ?
        """, (st.session_state.user_id,))
        
        stats = cursor.fetchone()
        if stats:
            total_scans = stats[0] if stats[0] else 0
            healthy_count = stats[1] if stats[1] else 0
            detected_count = stats[2] if stats[2] else 0
        
        conn.close()
        
    except Exception as e:
        # If database error, show 0
        st.warning(f"Could not load statistics: {e}")
        total_scans = 0
        healthy_count = 0
        detected_count = 0
    
    accuracy_rate = (healthy_count / total_scans * 100) if total_scans > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <img src="{stats_icon}" style="width: 40px; height: 40px; margin-bottom: 10px;">
            <div class="metric-value">{total_scans}</div>
            <div class="metric-label">Total Scans</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #28a745;">
            <img src="{healthy_icon}" style="width: 40px; height: 40px; margin-bottom: 10px;">
            <div class="metric-value" style="color: #28a745;">{healthy_count}</div>
            <div class="metric-label">Healthy Plants</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #dc3545;">
            <img src="{disease_icon}" style="width: 40px; height: 40px; margin-bottom: 10px;">
            <div class="metric-value" style="color: #dc3545;">{detected_count}</div>
            <div class="metric-label">Diseases Detected</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #ffc107;">
            <img src="{accuracy_icon}" style="width: 40px; height: 40px; margin-bottom: 10px;">
            <div class="metric-value" style="color: #ffc107;">{accuracy_rate:.1f}%</div>
            <div class="metric-label">Accuracy Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Recent Activity Section
    st.markdown("### Recent Activity")
    
    # GET REAL RECENT SCANS FROM HISTORY TABLE - DYNAMIC!
    recent_scans = []
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Query to get recent 3 scans from HISTORY table
        cursor.execute("""
            SELECT created_at, result, confidence
            FROM history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 3
        """, (st.session_state.user_id,))
        
        for row in cursor.fetchall():
            # Format the date
            from datetime import datetime
            try:
                date_obj = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                formatted_date = date_obj.strftime("%b %d, %Y")
            except:
                formatted_date = row[0]
            
            recent_scans.append({
                "date": formatted_date,
                "result": row[1],
                "confidence": f"{row[2]:.1f}%"
            })
        
        conn.close()
        
    except Exception as e:
        st.warning(f"Could not load recent activity: {e}")
        recent_scans = []
    
    # Display recent scans
    if recent_scans:
        for scan in recent_scans:
            result_color = "#28a745" if scan["result"] == "Healthy" else "#dc3545"
            st.markdown(f"""
            <div class="info-section">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: {result_color};">{scan["result"]}</strong>
                        <div style="color: #6c757d; font-size: 0.85rem;">{scan["date"]}</div>
                    </div>
                    <div style="color: #667eea; font-weight: bold;">
                        {scan["confidence"]}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No scan history yet. Start scanning to see your activity!")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Logout Button (Prominent)
    if st.button("Logout", use_container_width=True, type="primary"):
        # Clear session state
        st.session_state.page = "login"
        st.session_state.user_id = None
        st.session_state.logged_user = None
        st.success("Successfully logged out!")
        st.rerun()
    
    # Bottom Navigation
    show_bottom_nav('profile')