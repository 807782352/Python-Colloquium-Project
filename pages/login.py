import streamlit as st
from utils.utils import load_users, ensure_user, USERS_FILE

st.set_page_config(page_title="Login", page_icon="🔑")
st.subheader("Login")

user_id = st.text_input("User ID").strip().lower()
password = st.text_input("Password", type="password")

if st.button("Login"):
    users = load_users(USERS_FILE)
    user = ensure_user(user_id, users)

    if not user:
        st.error("User ID not found. Please sign up first!")
    else:
        if user.verify_password(password):   # User 类里要实现 verify_password
            st.success(f"Welcome {user.name}!")
            st.session_state["user"] = user
            st.switch_page("pages/dashboard.py")
        else:
            st.error("Incorrect password.")

if st.button("📝 Sign Up"):
    st.switch_page("pages/signup.py")
