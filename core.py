from core.user_management import load_users, save_users, authenticate, add_user
from core.property_management import load_properties, get_saved_properties, save_property_for_user

# --- Recommendation Logic (Stub: replace with your real logic) ---
def recommend_properties(user, top_k=5):
    # Returns top_k properties for demo; replace with real recommendation logic
    return load_properties()[:top_k]
