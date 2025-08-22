import os
import json

from models.users import User

BASE_DIR = os.path.dirname(__file__)              
PROJECT_ROOT = os.path.dirname(BASE_DIR)          
USERS_FILE = os.path.abspath(os.path.join(PROJECT_ROOT, "datasets", "users.json"))

def load_users(users_file=USERS_FILE):
    if not os.path.exists(users_file):
        return []
    with open(users_file, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_users(users, users_file=USERS_FILE):
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

def ensure_user(user_id, users):
    for u in users:
        if isinstance(u, User):
            if u.user_id == user_id:
                return u
        elif isinstance(u, dict):
            if u.get("user_id") == user_id:
                return User.from_dict(u)
    return None