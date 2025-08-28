import json
import os
import hashlib

USERS_FILE = os.path.join('datasets', 'users.json')

# Loads all users from the users.json file
def load_users():
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Saves the users list to the users.json file
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

# Authenticates a user by user_id and password (hashed)
def authenticate(user_id, password):
    users = load_users()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    for user in users:
        if user["user_id"] == user_id and user["password"] == hashed:
            return user
    return None

# Adds a new user to the users.json file
def add_user(user):
    users = load_users()
    users.append(user)
    save_users(users)
