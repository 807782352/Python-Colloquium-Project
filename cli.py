# --- User Dashboard Menu ---
def login_menu(user):
    """Display the user dashboard menu after login."""
    while True:
        print("\n" + "="*30)
        print("      USER DASHBOARD")
        print("="*30)
        print("1. User Profile Options")
        print("2. View Recommended Properties")
        print("3. View Saved Properties")
        print("4. Logout")
        print("="*30)
        choice = input("Enter your choice: ")
        if choice == '1':
            user_profile_options_menu(user)
        elif choice == '2':
            recommended_properties_menu(user)
        elif choice == '3':
            show_saved_properties(user)
        elif choice == '4':
            print("Logging out...")
            break
        else:
            print("Invalid choice. Please try again.")

# --- User Profile Options Menu ---
def user_profile_options_menu(user):
    while True:
        print("\n" + "*"*30)
        print("   USER PROFILE OPTIONS")
        print("*"*30)
        print("1. View Profile")
        print("2. Edit Profile")
        print("3. Delete Profile")
        print("4. Back")
        print("*"*30)
        sub_choice = input("Enter your choice: ")
        if sub_choice == '1':
            view_user_profile(user)
        elif sub_choice == '2':
            edit_user_profile(user)
            # After editing, stay in this menu
        elif sub_choice == '3':
            delete_user_profile(user)
            # After deleting, go to main menu
            main_menu()
            break
        elif sub_choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

# --- Show Recommended Properties ---
def show_recommended_properties(user):
    """Display recommended properties for the user."""
    print("\nRecommended Properties:")
    properties = load_properties()[:5]
    for prop in properties:
        print(f"{prop['type']} in {prop['location']} (ID: {prop['property_id']})")
        print(f"  Price per night: ${prop['price_per_night']}")
        print(f"  Features: {', '.join(prop['features'])}")
        print(f"  Tags: {', '.join(prop['tags'])}")
        print(f"  Booked Dates: {', '.join(prop.get('booked_dates', []))}")
        print(f"  Coordinates: {prop['coordinates']}")
        print()

# --- View User Profile ---
def view_user_profile(user):
    """Display the user's profile information."""
    print("\n" + "*"*30)
    print("      USER PROFILE")
    print("*"*30)
    print(f"User ID:              {user['user_id']}")
    print(f"Name:                 {user['name']}")
    print(f"Group Size:           {user['group_size']}")
    print(f"Preferred Environment:{user['preferred_environment']}")
    print(f"Budget:               {user['budget']}")
    print("*"*30 + "\n")

# --- Show Saved Properties ---
def show_saved_properties(user):
    """Display the user's saved properties."""
    saved = get_saved_properties(user['user_id'])
    if not saved:
        print("No properties saved yet.")
    for prop in saved:
        print(f"{prop['type']} in {prop['location']} (ID: {prop['property_id']})")
        print(f"  Price per night: ${prop['price_per_night']}")
        print(f"  Features: {', '.join(prop['features'])}")
        print(f"  Tags: {', '.join(prop['tags'])}")
        print(f"  Booked Dates: {', '.join(prop.get('booked_dates', []))}")
        print(f"  Coordinates: {prop['coordinates']}")
        print()
import os
import subprocess
from dotenv import load_dotenv
load_dotenv()
import sys
import hashlib
from core.user_management import load_users, save_users, authenticate, add_user
from core.property_management import load_properties, get_saved_properties, save_property_for_user

# --- Embedding DB Check and Creation ---
def ensure_embeddings_db():
    """Check and create the property embeddings database if needed."""
    import os, sqlite3
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Vector embeddings', 'property_vector_db.sqlite'))
    print(f"[LOG] Checking for embeddings DB at: {db_file}")
    if not os.path.exists(db_file):
        print("[LOG] Embeddings DB not found. Creating embeddings...")
        run_create_embeddings()
        return
    # Check if table exists
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    print("[LOG] Checking for property_embeddings table in DB...")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='property_embeddings'")
    exists = c.fetchone()
    conn.close()
    if not exists:
        print("[LOG] Embeddings table not found. Creating embeddings...")
        run_create_embeddings()
    else:
        print("[LOG] Embeddings DB and table found. Ready to use.")

# --- Run create_embeddings.py as a subprocess ---
def run_create_embeddings():
    """Run the embedding creation script as a subprocess."""
    import subprocess, sys
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Vector embeddings', 'create_embeddings.py'))
    print(f"[LOG] Running embedding creation script: {script_path}")
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    print("[LOG] Embedding script stdout:")
    print(result.stdout)
    if result.returncode != 0:
        print("[LOG] Error creating embeddings:", result.stderr)
        print("[LOG] Embedding creation script failed, but continuing to main logic.")
    else:
        print("[LOG] Embedding creation completed successfully or skipped (table exists). Continuing to main logic.")

# --- CLI Login ---
def cli_login():
    """Prompt user for login and authenticate."""
    users = load_users()
    user_id = input("Enter User ID: ")
    password = input("Enter Password: ")
    user = authenticate(user_id, password)
    if user:
        print(f"✅ Login successful! Welcome {user['name']}.")
        login_menu(user)
    else:
        print("❌ Invalid credentials.")
        main_menu()

# --- CLI Sign Up ---
def cli_sign_up():
    """Prompt user for sign up and create new user."""
    print("\n" + "="*30)
    print("      SIGN UP")
    print("="*30)
    user_id = input("Enter User ID: ")
    users = load_users()
    if any(user["user_id"] == user_id for user in users):
        print("❌ User ID already exists. Please try a different one.")
        return
    name = input("Enter Name: ")
    group_size = input("Enter Group Size: ")
    pref_input = input("Enter Preferred Environment(s) (comma-separated): ")
    preferred_environment = [pref.strip() for pref in pref_input.split(',') if pref.strip()]
    budget = input("Enter Budget: ")
    password = input("Create Password: ")
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    new_user = {
        "user_id": user_id,
        "name": name,
        "group_size": group_size,
        "preferred_environment": preferred_environment,
        "budget": budget,
        "password": hashed_password
    }
    add_user(new_user)
    print(f"✅ Sign up successful! Welcome {name}. You can now log in.")

# --- Main Menu ---
def main_menu():
    """Display the main menu for the CLI app."""
    print("\n" + "="*30)
    print("   PROPERTY LISTING APP")
    print("="*30)
    print("1. Login")
    print("2. Sign Up")
    print("3. Exit")
    print("="*30)
    choice = input("Enter your choice: ")
    if choice == '1':
        cli_login()
    elif choice == '2':
        cli_sign_up()
        main_menu()
    elif choice == '3':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice. Please try again.")
        main_menu()

# --- Launcher ---
def launcher():
    """Entry point for the CLI and UI launcher."""
    print("\n" + "="*40)
    print("Welcome to Gr8 Summer Stays!")
    print("="*40)
    print("1. Launch CLI")
    print("2. Launch UI (Streamlit)")
    print("3. Exit")
    print("="*40)
    choice = input("Enter your choice: ")
    if choice == '1':
        main_menu()
    elif choice == '2':
        print("Launching Streamlit UI...")
        # venv_streamlit = os.path.join(os.path.dirname(sys.executable), 'streamlit')
        # cmd = f'"{venv_streamlit}" run Gr8-Summer-Stays/app.py'
        # os.system(cmd)
        subprocess.run([sys.executable, "-m", "streamlit", "run", "Gr8-Summer-Stays/app.py"])
    elif choice == '3':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice. Please try again.")
        launcher()

# --- Recommended Properties Menu ---
def recommended_properties_menu(user):
    """Show submenu for recommended properties: view or chat with AI."""
    while True:
        print("\n--- Recommended Properties ---")
        print("1. Show recommended properties (based on your profile)")
        print("2. Chat with AI travel agent")
        print("3. Back")
        sub_choice = input("Enter your choice: ")
        if sub_choice == '1':
            show_recommended_properties(user)
        elif sub_choice == '2':
            chat_with_ai_travel_agent(user)
        elif sub_choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")

import requests
import os

def chat_with_ai_travel_agent(user):
    """AI travel agent chat using OpenRouter LLM API."""
    print("\n--- AI Travel Agent Chat ---")
    print("Type 'exit' to leave the chat.")
    chat_history = []

    # Import SBERT recommender
    try:
        from recommenders.sbert_recommender import SbertRecommender
    except ImportError:
        print("[ERROR] Could not import SbertRecommender. Make sure recommenders/sbert_recommender.py exists.")
        return

    # Load properties and initialize SBERT recommender
    properties = load_properties()
    recommender = SbertRecommender(properties)

    while True:
        user_input = input("You: ")
        if user_input.strip().lower() == 'exit':
            print("Exiting AI chat.")
            break
        chat_history.append({"role": "user", "content": user_input})

        # Use the user's query as the SBERT search input
        # Compose a pseudo-user object for SBERT (for budget filtering)
        class QueryUser:
            def __init__(self, user, query):
                self.user_id = user.get('user_id')
                self.preferred_environment = [query]
                try:
                    self.budget = float(user.get('budget', 0))
                except Exception:
                    self.budget = 0
        query_user = QueryUser(user, user_input)
        top_props = recommender.recommend_logic(query_user, top_n=5)
        # Summarize top properties for LLM context
        prop_summaries = []
        for p in top_props:
            prop_summaries.append(f"{p['type']} in {p['location']} (${p['price_per_night']}/night), features: {', '.join(p['features'])}, tags: {', '.join(p['tags'])}")
        prop_context = "\n".join(prop_summaries) if prop_summaries else "No matching properties found."

        # Build context string from last 6 messages
        history = chat_history[-6:]
        context_str = "\n".join([
            ("User: " + m["content"]) if m["role"] == "user" else ("AI: " + m["content"]) for m in history
        ])
        prompt = (
            f"User profile: {user}.\n"
            f"Top properties matching your query:\n{prop_context}\n"
            f"Chat history:\n{context_str}\nUser: {user_input}"
        )
        print("AI is thinking...")
        ai_response = query_openrouter_deepseek_llm(prompt)
        chat_history.append({"role": "assistant", "content": ai_response})
        print(f"AI: {ai_response}")

# Query the OpenRouter LLM API (copied from UI)
def query_openrouter_deepseek_llm(prompt):
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    API_KEY = os.environ.get("OPENROUTER_API_KEY")
    if not API_KEY:
        return "[ERROR] OpenRouter API key not set. Please set the OPENROUTER_API_KEY environment variable or add it to a .env file."
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Python-Colloquium-Project"
    }
    payload = {
        "model": "mistralai/mistral-large",
        "messages": [
            {"role": "system", "content": "You are a helpful AI travel agent assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 600
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and data["choices"] and "message" in data["choices"][0]:
                return data["choices"][0]["message"]["content"]
            else:
                return "[ERROR] No response from DeepSeek LLM."
        else:
            return f"[ERROR] LLM API error: {response.status_code} {response.text}"
    except Exception as e:
        return f"[ERROR] LLM API exception: {e}"

# --- Edit User Profile ---
def edit_user_profile(user):
    print("\nEditing Profile:")
    name = input(f"Name [{user['name']}]: ") or user['name']
    group_size = input(f"Group Size [{user['group_size']}]: ") or user['group_size']
    preferred_env = input(f"Preferred Environment(s) (comma-separated) [{', '.join(user['preferred_environment'])}]: ")
    if preferred_env:
        preferred_environment = [e.strip() for e in preferred_env.split(',') if e.strip()]
    else:
        preferred_environment = user['preferred_environment']
    budget = input(f"Budget [{user['budget']}]: ") or user['budget']
    user['name'] = name
    user['group_size'] = group_size
    user['preferred_environment'] = preferred_environment
    user['budget'] = budget
    users = load_users()
    for u in users:
        if u['user_id'] == user['user_id']:
            u.update(user)
    save_users(users)
    print("✅ Profile updated!")

# --- Delete User Profile ---
def delete_user_profile(user):
    confirm = input("Are you sure you want to delete your profile? This cannot be undone. (y/n): ")
    if confirm.lower() == 'y':
        users = load_users()
        users = [u for u in users if u['user_id'] != user['user_id']]
        save_users(users)
        print("✅ Profile deleted. Returning to main menu.")
    else:
        print("Profile deletion cancelled.")
