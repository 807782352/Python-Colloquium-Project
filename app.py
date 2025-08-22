import streamlit as st
import os, base64

BASE_DIR = os.path.dirname(__file__)
IMAGE_PATH = os.path.abspath(os.path.join(BASE_DIR, "images"))
LOGO = os.path.abspath(os.path.join(IMAGE_PATH, "logo.png"))

st.set_page_config(page_title="GR8 Property Listing", page_icon="🏠")

# --- Global styles ---
st.markdown(
    """
    <style>
    body, .stApp {
        background: linear-gradient(135deg, #faffff 0%, #f0f7ff 100%) !important;
        font-family: Arial, Helvetica, sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: Arial, Helvetica, sans-serif;
        font-weight: 700;
        color: #222;
    }
    p {
        color: #444;
    }

    .stButton > button {
        all: unset;
        background: linear-gradient(135deg, #6dd5fa 0%, #ffffff 100%);
        border: none;
        padding: 12px 28px;
        border-radius: 12px;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        width: 100px;
        text-align: center;
        color: #222;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #4facfe 0%, #6dd5fa 100%);
        color: white;
        transform: translateY(-3px);
        box-shadow: 0px 6px 18px rgba(0,0,0,0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Centered logo ---
with open(LOGO, "rb") as img_file:
    img_base64 = base64.b64encode(img_file.read()).decode()

st.markdown(
    f"""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="data:image/png;base64,{img_base64}" width="120" alt="GR8 logo"/>
        <h1 style="margin-top:10px;">GR8 Property Listing</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Welcome copy ---
st.markdown(
    """
    <div style="text-align:center; margin:20px 0 40px 0;">
        <h2 style="margin-bottom:10px;">Welcome to GR8 Property Recommender</h2>
        <p style="font-size:1.2rem;">
            Discover your ideal property with ease and confidence.
        </p>
        <p style="font-size:1.1rem; color:#666;">
            Please login or sign up to get started.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Button layout (left & right) ---
col1, col2, col3 = st.columns([1, 3, 1])

with col1:  # left-aligned
    if st.button("🔑 Login", key="login_btn"):
        st.switch_page("pages/login.py")

with col3:  # right-aligned
    if st.button("📝 Sign Up", key="signup_btn"):
        st.switch_page("pages/signup.py")
