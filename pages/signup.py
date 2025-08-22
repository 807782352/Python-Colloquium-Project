import streamlit as st
import hashlib
from utils.utils import load_users, save_users, ensure_user, USERS_FILE

st.set_page_config(page_title="Sign Up", page_icon="📝")

st.subheader("Sign Up")

new_user_id = st.text_input("New User ID").lower().strip()
name = st.text_input("Name")
group_size = st.text_input("Group Size")
preferred_environment = st.text_input("Preferred Environment(s) (comma-separated)")
budget = st.text_input("Budget")
password = st.text_input("Password", type="password")

if st.button("Create Account"):
    users = load_users(USERS_FILE)
    if ensure_user(new_user_id, users):
        st.error("User ID already exists.")
    else:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        new_user = {
            "user_id": new_user_id,
            "name": name,
            "group_size": group_size,
            "preferred_environment": [
                pref.strip() for pref in preferred_environment.split(",") if pref.strip()
            ],
            "budget": budget,
            "password_hash": hashed_password,
        }
        users.append(new_user)
        save_users(users, USERS_FILE)
        st.success("Sign up successful! Redirecting to login...")
        st.switch_page("pages/login.py")   # 👈 注册成功后跳转到登录
