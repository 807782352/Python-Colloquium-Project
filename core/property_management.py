import json
import os

PROPERTIES_FILE = os.path.join('datasets', 'property_listings.json')
USERS_FILE = os.path.join('datasets', 'users.json')

# Loads all properties from the property_listings.json file
def load_properties():
    with open(PROPERTIES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)["properties"]

# Gets saved properties for a user by user_id
def get_saved_properties(user_id):
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)
    properties = load_properties()
    for user in users:
        if user["user_id"] == user_id:
            saved_ids = user.get("saved_property", [])
            return [p for p in properties if p.get("property_id") in saved_ids]
    return []

# Saves a property to a user's saved_property list
def save_property_for_user(user_id, property_id):
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)
    updated = False
    for user in users:
        if user["user_id"] == user_id:
            if "saved_property" not in user:
                user["saved_property"] = []
            if property_id not in user["saved_property"]:
                user["saved_property"].append(property_id)
                updated = True
    if updated:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
