# main.py
# Entry point for the property listing application.
# Provides a simple CLI for user login and sign up.

from recommenders.sbert_recommender import SbertRecommender
from models.users import User
from utils.utils import load_users, save_users, ensure_user

import json
import hashlib
import os
import sys
import subprocess
import argparse
import shutil

BASE_DIR = os.path.dirname(__file__)

# Path to the users JSON file
USERS_FILE = os.path.abspath(
    os.path.join(BASE_DIR, "datasets", "users.json")
)  # Change this path if your file is elsewhere

# Path to the property listings JSON file (robust to script location)
PROPERTIES_FILE = os.path.abspath(
    os.path.join(BASE_DIR, "datasets", "property_listings.json")
)

_RECOMMENDER = None  # Placeholder for the recommender instance

# def load_users(users_file):
#     """
#     Load users from a JSON file.
#     Returns a list of user dictionaries.
#     """
#     if not os.path.exists(users_file):
#         return []
#     with open(users_file, 'r') as f:
#         try:
#             return json.load(f)
#         except json.JSONDecodeError:
#             return []

# def save_users(users, users_file):
#     """
#     Save users to a JSON file.
#     user: user dictionaries.
#     """
#     with open(users_file, 'w') as f:
#         json.dump([u for u in users], f, indent=4)

# def ensure_user(user_id, users):
#     """
#     Ensure a user exists in the users list by user_id.
#     """
#     for u in users:
#         if isinstance(u, User):
#             if u.user_id == user_id:
#                 return u
#         elif isinstance(u, dict):
#             if u.get("user_id") == user_id:
#                 return User.from_dict(u)
#     return None


def login(user, raw_password, users, max_attempts=3):
    """
    Handle user login.
    """
    while max_attempts > 0:
        # hashed_input = hashlib.sha256(password.encode()).hexdigest()

        if user.verify_password(raw_password):
            print(f"✅ Login successful! Welcome {user.name}.")
            login_menu(user, users)
            return
        else:
            max_attempts -= 1
            if max_attempts > 0:
                print(f"❌ Incorrect password. You have {max_attempts} attempts left.")
                raw_password = input("Please enter your password again: ")
            else:
                print("❌ Too many failed attempts. Please try again later.")
                return
    main_menu()


def sign_up():
    """
    Handle user sign up.
    Prompts for user details and saves them to the users JSON file.
    """
    users = load_users(USERS_FILE)
    print("\n" + "=" * 30)
    print("      SIGN UP")
    print("=" * 30)

    user_id = input("Enter User ID: ").lower().strip()
    if ensure_user(user_id, users):
        print("❌ User ID already exists. Please try a different one.")
        return

    name = input("Enter Name: ")
    group_size = input("Enter Group Size: ")
    pref_input = input("Enter Preferred Environment(s) (comma-separated): ")
    preferred_environment = [
        pref.strip() for pref in pref_input.split(",") if pref.strip()
    ]
    budget = input("Enter Budget: ")

    password = input("Create Password: ").strip()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    new_user = {
        "user_id": user_id,
        "name": name,
        "group_size": group_size,
        "preferred_environment": preferred_environment,
        "budget": budget,
        "password_hash": hashed_password,
    }

    users.append(new_user)

    # Write the updated users list back to the JSON file
    save_users(users, USERS_FILE)

    print(f"✅ Sign up successful! Welcome {name}. You can now log in.")


def login_menu(user, users):
    print("\n" + "=" * 30)
    print("      USER DASHBOARD")
    print("=" * 30)
    print("1. View User Profile")
    print("2. View Property Listings")
    print("3. Logout")
    print("=" * 30)
    choice = input("Enter your choice: ")
    if choice == "1":
        manage_user_profile(user, users)
    elif choice == "2":
        property_listings_menu(user, users)
    elif choice == "3":
        main_menu()
    else:
        print("Invalid choice. Please try again.")
        login_menu(user, users)


def get_recommender():
    """
    Initialize and return the SbertRecommender instance. (LAZY LOADING)
    This function ensures that the recommender is only created once.
    """
    global _RECOMMENDER
    if _RECOMMENDER is None:
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        properties = data.get("properties", [])
        _RECOMMENDER = SbertRecommender(properties)
    return _RECOMMENDER


# --- Property Listings Menu ---
def property_listings_menu(user, users):

    recommender = get_recommender()  # Lazy load the recommender
    top_n = 5

    print("\n" + "-" * 30)
    print("   PROPERTY LISTINGS")
    print("-" * 30)
    print("1. Get recommended options according to your preferences")
    print("2. Chat with the AI travel agent to plan your vacation")
    print("3. Back")
    print("-" * 30)
    choice = input("Enter your choice: ")
    if choice == "1":
        if user:
            recommended_properties = recommender.recommend_logic(user, top_n)
            show_properties_with_descriptions(recommended_properties, user)
            print("\nNow starting chat with the AI travel agent...\n")
            travel_agent_chat(user, user, recommended_properties)
        else:
            print("User not found.")
    elif choice == "2":
        if user:
            travel_agent_chat(user, users)
        else:
            print("User not found.")
    elif choice == "3":
        login_menu(user, users)
    else:
        print("Invalid choice.")
        property_listings_menu(user, users)


# --- Vector Search Recommendation Logic (Deprecated)---
def recommend_properties_by_preferences(user, top_k=3):
    import sys, importlib.util, os

    embeddings_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "Vector embeddings", "create_embeddings.py"
        )
    )
    spec = importlib.util.spec_from_file_location("create_embeddings", embeddings_path)
    create_embeddings = importlib.util.module_from_spec(spec)
    sys.modules["create_embeddings"] = create_embeddings
    spec.loader.exec_module(create_embeddings)
    # Compose a query from user preferences
    if isinstance(user["preferred_environment"], list):
        query = " ".join(user["preferred_environment"])
    else:
        query = str(user["preferred_environment"])
    query += f" {user['group_size']} {user['budget']}"
    model = create_embeddings.get_embedding_model()
    db_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "Vector embeddings", "property_vector_db.sqlite"
        )
    )
    results = create_embeddings.search_property(query, db_file, model, top_k=top_k)
    return results


# --- Show Properties with Appealing Descriptions ---
def show_properties_with_descriptions(properties, user):
    print("\nRecommended Properties:")
    for prop in properties:
        description = generate_property_description(prop, user)
        print(
            f"\nProperty ID: {prop['property_id']} | Similarity: {prop['similarity']:.4f}"
        )
        print(f"  Location: {prop['location']}")
        print(f"  Type: {prop['type']}")
        print(f"  Features: {prop['features']}")
        print(f"  Tags: {prop['tags']}")
        print(f"  Description: {description}")


# --- OpenRouter DeepSeek LLM API ---
def query_openrouter_deepseek_llm(prompt):
    import requests, os

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # If dotenv is not installed, skip silently
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    API_KEY = os.environ.get("OPENROUTER_API_KEY")
    if not API_KEY:
        return "[ERROR] OpenRouter API key not set. Please set the OPENROUTER_API_KEY environment variable or add it to a .env file."
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Python-Colloquium-Project",
    }
    payload = {
        "model": "mistralai/mistral-large",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI travel agent assistant.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if (
                "choices" in data
                and data["choices"]
                and "message" in data["choices"][0]
            ):
                return data["choices"][0]["message"]["content"]
            else:
                return "[ERROR] No response from DeepSeek LLM."
        else:
            return f"[ERROR] LLM API error: {response.status_code} {response.text}"
    except Exception as e:
        return f"[ERROR] LLM API exception: {e}"


# --- Generate Appealing Description using DeepSeek LLM ---
def generate_property_description(property_data, user):
    # Short, concise description (30-40 words max)
    features = ", ".join(property_data["features"][:4])
    tags = ", ".join(property_data["tags"][:3])
    desc = (
        f"A {property_data['type']} in {property_data['location']} with {features}. "
        f"Great for {tags}. "
        f"Enjoy comfort and adventure at ${property_data.get('price', 'your budget')} per night."
    )
    # Ensure description is about 30-40 words
    words = desc.split()
    if len(words) > 40:
        desc = " ".join(words[:40]) + "..."
    return desc


# --- AI Travel Agent Chat ---
def travel_agent_chat(user, users, recommended_properties=None):
    print("\n--- Welcome to the AI Travel Agent! ---")
    print("Type 'exit' to end the chat.")
    chat_history = []
    # Prepare context string for the LLM
    if recommended_properties:
        context_str = f"Here are {len(recommended_properties)} recommended properties for the user: "
        for idx, prop in enumerate(recommended_properties, 1):
            context_str += f"\nProperty #{idx}: ID: {prop['property_id']}, Location: {prop['location']}, Type: {prop['type']}, Features: {prop['features']}, Tags: {prop['tags']}"
    else:
        context_str = "No recommended properties yet."
    property_id_map = (
        {prop["property_id"]: prop for prop in recommended_properties}
        if recommended_properties
        else {}
    )
    while True:
        user_input = input("\033[96mYou:\033[0m ")  # Cyan for user
        if user_input.lower() == "exit":
            print(
                "\033[92mAI: Thanks for using AI Travel Agent!\033[0m"
            )  # Green for AI
            login_menu(user, users)
            return

        # [TODO: Have not check if the recommended logic works with the chat agent]
        # Check if user refers to a recommended property by ID
        found = False
        matched_prop = None
        if property_id_map:
            for pid, prop in property_id_map.items():
                if pid.lower() in user_input.lower():
                    found = True
                    matched_prop = prop
                    print(
                        f"\033[92mAI: Here are the details for property ID {pid}:\033[0m"
                    )
                    print(f"  Location   : {prop['location']}")
                    print(f"  Type       : {prop['type']}")
                    print(f"  Features   : {prop['features']}")
                    print(f"  Tags       : {prop['tags']}")
                    print(f"  Similarity : {prop['similarity']:.4f}")
                    print(f"  Description: {generate_property_description(prop, user)}")
                    break
        # Rule-based weather answer if user asks about weather for a property
        if ("weather" in user_input.lower() or "climate" in user_input.lower()) and (
            found or recommended_properties
        ):
            if not matched_prop and recommended_properties:
                matched_prop = recommended_properties[0]
            if matched_prop:
                location = matched_prop["location"].lower()
                tags = (
                    matched_prop["tags"].lower()
                    if isinstance(matched_prop["tags"], str)
                    else str(matched_prop["tags"]).lower()
                )
                # Simple rule-based weather summary
                if "mountain" in location or "mountain" in tags:
                    weather = "Expect cool to cold temperatures, especially at night. Weather can change quickly in the mountains."
                elif "desert" in location or "desert" in tags:
                    weather = (
                        "Expect hot days and cool nights. Summers can be extremely hot."
                    )
                elif "beach" in location or "beach" in tags or "ocean" in tags:
                    weather = "Generally mild and breezy, with pleasant temperatures."
                elif "city" in tags:
                    weather = "Typical urban climate, varies by season."
                elif "temperate" in location or "temperate" in tags:
                    weather = "Mild temperatures, not too hot or cold."
                elif "cold" in location or "cold" in tags:
                    weather = "Cold climate, especially in winter. Snow is possible."
                else:
                    weather = "Weather is generally pleasant, but check the forecast for details."
                print(
                    f"\033[92mAI: The weather at {matched_prop['location']} is: {weather}\033[0m"
                )
                chat_history.append((user_input, weather))
                continue
        if found:
            continue
        # Otherwise, use LLM for general questions
        short_context = "Here are some recommended properties: "
        if recommended_properties:
            for idx, prop in enumerate(recommended_properties, 1):
                short_context += f"\nProperty #{idx}: {prop['type']} in {prop['location']} (ID: {prop['property_id']})"
        else:
            short_context = "No recommended properties yet."
        # Limit chat history to last 2 turns
        limited_history = chat_history[-2:] if len(chat_history) > 2 else chat_history
        history_str = "\n".join([f"User: {u}\nAI: {a}" for u, a in limited_history])
        prompt = (
            f"You are an AI travel agent. The user profile is: {user}. "
            f"{short_context}\n"
            f"Chat history:\n{history_str}\n"
            f"User: {user_input}\nAI:"
        )
        response = query_openrouter_deepseek_llm(prompt)
        if not response or response.strip() == "":
            print(
                "\033[92mAI: [No response from LLM. Please try again or check API status.]\033[0m"
            )
        elif response.startswith("[ERROR]"):
            print(f"\033[91mAI: {response}\033[0m")  # Red for errors
        else:
            print(f"\033[92mAI: {response.strip()}\033[0m")
        chat_history.append((user_input, response.strip() if response else ""))


# --- Extract Keywords using LLM (DeepSeek) ---
def extract_keywords_with_llm(prompt):
    extraction_prompt = f"Extract the main keywords and preferences from this travel request: '{prompt}'. Return a comma-separated list."
    response = query_openrouter_deepseek_llm(extraction_prompt)
    return response.strip()


# --- Recommend Properties by Prompt ---
def recommend_properties_by_prompt(prompt, top_k=3):
    import sys, importlib.util, os

    embeddings_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "Vector embeddings", "create_embeddings.py"
        )
    )
    spec = importlib.util.spec_from_file_location("create_embeddings", embeddings_path)
    create_embeddings = importlib.util.module_from_spec(spec)
    sys.modules["create_embeddings"] = create_embeddings
    spec.loader.exec_module(create_embeddings)
    model = create_embeddings.get_embedding_model()
    db_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "Vector embeddings", "property_vector_db.sqlite"
        )
    )
    results = create_embeddings.search_property(prompt, db_file, model, top_k=top_k)
    return results


# --- Weather Suitability Check (Rule-based) ---
def check_weather_suitability(properties):
    import datetime

    if not properties:
        return ""
    prop = properties[0]
    location = prop["location"].lower()
    tags = (
        prop["tags"].lower()
        if isinstance(prop["tags"], str)
        else str(prop["tags"]).lower()
    )
    month = datetime.datetime.now().month
    if ("desert" in location or "hot" in tags) and month in [6, 7, 8]:
        return "Note: This destination may be very hot in summer. Consider if this suits your comfort."
    if ("mountain" in location or "cold" in tags) and month in [12, 1, 2]:
        return "Note: This destination may be very cold in winter. Pack accordingly!"
    return "Weather looks suitable for your trip!"


# --- Itinerary Preferences ---
def ask_itenary_preferences():
    print("AI: Would you like me to generate an itinerary for your trip?")
    resp = input("(yes/no): ")
    if resp.lower() == "yes":
        days = input("How many days is your trip?: ")
        style = input("What kind of itinerary do you want? (energetic/relaxed/mixed): ")
        extras = input(
            "Do you want recommendations for restaurants, activities, or anything else? (yes/no): "
        )
        print(
            f"AI: Great! I'll prepare a {style} itinerary for {days} days. I'll also include extra recommendations: {extras}."
        )
        print("(Itinerary generation coming soon!)")
    else:
        print("AI: No problem! Let me know if you need anything else.")


def manage_user_profile(user, users):
    print("\n" + "-" * 30)
    print("   MANAGE USER PROFILE")
    print("-" * 30)
    print("1. View Profile")
    print("2. Edit Profile")
    print("3. Delete Profile")
    print("4. Back to Main Menu")
    print("-" * 30)
    choice = input("Enter your choice: ")
    if choice == "1":
        view_user_profile(user, users)
        manage_user_profile(user, users)
    elif choice == "2":
        edit_user_profile(user, users)
        manage_user_profile(user, users)
    elif choice == "3":
        delete_user_profile(user, users)
        main_menu()
    elif choice == "4":
        login_menu(user, users)
    else:
        print("Invalid choice.")
        manage_user_profile(user, users)


def view_user_profile(user, users):
    """
    Display the user's profile information.
    """
    print("\n" + "*" * 30)
    print("      USER PROFILE")
    print("*" * 30)
    print(f"User ID:              {user.user_id}")
    print(f"Name:                 {user.name}")
    print(f"Group Size:           {user.group_size}")
    print(f"Preferred Environment:{', '.join(user.preferred_environment)}")
    print(f"Budget:               {user.budget}")
    print("*" * 30 + "\n")


def edit_user_profile(user, users):
    """
    Edit the user's profile information.
    """
    print("\n" + "-" * 30)
    print("      EDIT PROFILE")
    print("-" * 30)
    name = input(f"Name ({user.name}): ") or user.name

    group_input = input(f"Group Size ({user.group_size}): ")
    group_size = group_input or user.group_size

    pref_input = input(
        f"Preferred Environment(s) (comma-separated) ({user.preferred_environment}): "
    )
    if pref_input:
        # Split by comma, strip whitespace, and filter out empty strings
        preferred_environment = [
            pref.strip() for pref in pref_input.split(",") if pref.strip()
        ]
    else:
        preferred_environment = user.preferred_environment

    budget_input = input(f"Budget ({user.budget}): ")
    budget = budget_input or user.budget

    # Update the user object
    user.name = name
    user.group_size = group_size
    user.preferred_environment = preferred_environment
    user.budget = budget

    for i, u in enumerate(users):
        if u.get("user_id") == user.user_id:
            users[i] = user.to_dict()
            break

    # Write the updated users list back to the JSON file
    save_users(users, USERS_FILE)
    print("\nProfile updated successfully.\n")


def delete_user_profile(user, users):
    """
    Delete the user's profile.
    """
    confirm = (
        input(f"⚠️ Are you sure you want to delete profile for {user.name}? (y/n): ")
        .strip()
        .lower()
    )
    if confirm != "y":
        print("❎ Deletion cancelled.")
        return

    for u in users:
        if u.get("user_id") == user.user_id:
            users.remove(u)
            save_users(users, USERS_FILE)
            print(f"\n✅ Profile for {user.name} deleted successfully.\n")
            return


def main_menu():
    """
    Display the main menu and handle user input for login or sign up.
    """
    while True:
        print("\n" + "=" * 30)
        print("   PROPERTY LISTING APP")
        print("=" * 30)
        print("1. Login")
        print("2. Sign Up")
        print("3. Exit")
        print("=" * 30)
        choice = input("Enter your choice: ")

        if choice == "1":
            users = load_users(USERS_FILE)
            entered_user_id = input("Enter User ID: ").lower().strip()
            user = ensure_user(entered_user_id, users)
            if not user:
                print("❌ User ID not found. Please sign up first!")
                continue
            entered_password = input("Enter Password: ").strip()
            login(user, entered_password, users)

        elif choice == "2":
            sign_up()
        elif choice == "3":
            print("Thank you for choosing our app! See you again!")
            break
        else:
            print("Invalid choice. Please try again.")


# ---------- helpers ----------
def in_streamlit_runtime() -> bool:
    """Detect if this process is already running under Streamlit."""
    argv = " ".join(sys.argv).lower()
    if "streamlit" in argv and "run" in argv:
        return True
    # Env hints set by Streamlit server (defensive)
    for k in ("STREAMLIT_RUNTIME", "STREAMLIT_SERVER_PORT", "STREAMLIT_SERVER_ADDRESS"):
        if os.environ.get(k):
            return True
    return False


def ensure_streamlit():
    if shutil.which("streamlit") is None:
        raise SystemExit(
            "Streamlit is not installed.\n"
            "  pip install streamlit\n"
            "Or run in CLI mode:  python main.py --mode cli"
        )


GUI_PATH = os.path.join(os.path.dirname(__file__), "app.py")


def launch_gui(passthrough=None):
    """Start Streamlit on app.py using the current Python interpreter."""
    ensure_streamlit()
    cmd = [sys.executable, "-m", "streamlit", "run", GUI_PATH]
    if passthrough:
        cmd += passthrough  # forward flags after `--`
    print("🚀 Launching GUI:\n  " + " ".join(cmd))
    subprocess.run(cmd, check=False)


def run_cli():
    """Your CLI entrypoint."""
    print("🖥️  Running CLI ...")
    main_menu()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launcher (CLI / GUI)",
        epilog=(
            "Examples:\n"
            "  python main.py --mode gui\n"
            "  python main.py --mode cli\n"
            "  GR8_MODE=gui python main.py\n"
            "  python main.py --mode gui -- --server.port 8502 --server.headless true"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "gui", "cli", "prompt"],
        default=os.environ.get("GR8_MODE", "auto").lower(),
        help="gui | cli | auto | prompt (default: %(default)s)",
    )
    # everything after `--` goes to Streamlit
    args, passthrough = parser.parse_known_args()
    return args, passthrough



# -----------------------------------------------------------------------------
# Launcher that can run either:
#   - CLI mode: plain Python console
#   - GUI mode: Streamlit app (in a separate app.py file)
#
# Usage examples:
#   python main.py --mode gui
#   python main.py --mode cli
#   python main.py                  # auto: prefer CLI in TTY, GUI otherwise
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    args, passthrough = parse_args()

    # If someone ran:  streamlit run main.py
    if in_streamlit_runtime():
        # Directly render the GUI code inside Streamlit runtime.
        import app  # this executes app.py

        sys.exit(0)

    mode = args.mode

    if mode == "prompt":
        choice = input("Choose mode [gui/cli] (default gui): ").strip().lower() or "gui"
        mode = "cli" if choice == "cli" else "gui"

    if mode == "gui":
        launch_gui(passthrough)
        sys.exit(0)

    if mode == "cli":
        run_cli()
        sys.exit(0)

    # auto mode: prefer CLI in interactive TTY, else GUI
    if sys.stdout.isatty():
        run_cli()
    else:
        launch_gui(passthrough)
