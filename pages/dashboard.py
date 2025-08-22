# pages/dashboard.py
import json
from pathlib import Path
from types import SimpleNamespace

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, BeautifyIcon

# ====================== BASIC SETTINGS ======================
st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# Global CSS (hide default nav + light styling)
st.markdown(
    """
<style>
div[data-testid="stSidebarNav"] { display: none !important; }
body, .stApp { font-family: Arial, Helvetica, sans-serif; }

.gr8-card {
  background: #fff;
  border: 1px solid #e7eef6;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.gr8-chip {
  display:inline-block; padding: 4px 10px; border-radius:9999px;
  background:#f3f7ff; color:#1d4ed8; font-size:.8rem; margin-right:6px;
  border:1px solid #e0eaff;
}
.profile-card .row { display:flex; align-items:center; }
.profile-avatar {
  width:48px; height:48px; border-radius:9999px; background:#e0f2fe;
  color:#0369a1; display:flex; align-items:center; justify-content:center;
  font-weight:700;
}
.profile-name { font-weight:700; color:#111827; }
.profile-sub  { color:#6b7280; font-size:.9rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ====================== SIGN-IN CHECK ======================
if "user" not in st.session_state or not st.session_state["user"]:
    st.warning("You are not logged in. Redirecting to login page...")
    st.switch_page("pages/login.py")
    st.stop()

# Ensure map version exists (used to force remount of map component)
if "map_version" not in st.session_state:
    st.session_state.map_version = 0

# ====================== HELPERS (GLOBAL) ======================
_CANON_KEYS = {"user_id", "name", "group_size", "budget", "preferred_environment", "password_hash"}

def fmt_money(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return str(x)

def as_dict_any(u):
    """Make a dict from user; drop private (_*) attrs and backfill common fields."""
    if isinstance(u, dict):
        d = dict(u)
    else:
        try:
            d = dict(vars(u))
        except Exception:
            d = {}
        # Backfill common fields from attributes if present
        for k in ["user_id", "name", "group_size", "budget", "preferred_environment", "preferred_environemnts", "password_hash"]:
            if k not in d and hasattr(u, k):
                d[k] = getattr(u, k)
    # Drop private keys (underscore-prefixed)
    d = {k: v for k, v in d.items() if not str(k).startswith("_")}
    return d

def canonicalize_user_dict(d: dict) -> dict:
    """Normalize keys/types; handle typos; dedupe tags; keep only canonical keys."""
    out = dict(d)

    # Handle misspelled field names
    if "preferred_environemnts" in out and "preferred_environment" not in out:
        out["preferred_environment"] = out.pop("preferred_environemnts")

    # Build canonical payload
    canon = {}
    canon["user_id"] = str(out.get("user_id", "user"))
    canon["name"] = out.get("name", "User")

    # group_size -> int
    try:
        canon["group_size"] = int(out.get("group_size", 1))
    except Exception:
        canon["group_size"] = 1

    # budget -> float
    try:
        canon["budget"] = float(out.get("budget", 0) or 0)
    except Exception:
        canon["budget"] = 0.0

    # preferred_environment -> list[str], clean + dedupe (case-insensitive)
    pe = out.get("preferred_environment", [])
    if isinstance(pe, str):
        pe = [pe]
    seen, cleaned = set(), []
    for x in pe:
        s = str(x).strip()
        if not s:
            continue
        k = s.lower()
        if k not in seen:
            seen.add(k)
            cleaned.append(s)
    canon["preferred_environment"] = cleaned

    # password_hash is optional
    if "password_hash" in out:
        canon["password_hash"] = out["password_hash"]

    return canon

def ensure_attr_user(u_dict_or_obj):
    """
    Return a dot-accessible user object that the recommender can consume.
    - If all canonical fields on a class instance are writable, update it in place.
    - If any field is read-only (property without setter), fall back to a SimpleNamespace.
    - If input is a dict, always wrap it in SimpleNamespace.
    """
    d = canonicalize_user_dict(as_dict_any(u_dict_or_obj))

    # Dict → always wrap
    if isinstance(u_dict_or_obj, dict):
        return SimpleNamespace(**d)

    # If it's not a dict, try in-place update only when attributes are writable
    obj = u_dict_or_obj

    def _is_writable(o, name):
        """Heuristic: property must have fset; otherwise assume writable."""
        try:
            attr = getattr(o.__class__, name, None)
            if isinstance(attr, property):
                return attr.fset is not None  # property without setter → read-only
            # Non-property attribute: assume writable (or will be created)
            return True
        except Exception:
            return False

    # If any canonical field is not writable, return a wrapper instead of mutating
    if not all(_is_writable(obj, k) for k in d.keys()):
        return SimpleNamespace(**d)

    # Safe to mutate in place; if any setattr still fails, fall back to wrapper
    try:
        for k, v in d.items():
            setattr(obj, k, v)
        return obj
    except Exception:
        return SimpleNamespace(**d)

def save_users_to_json(updated_user_obj_or_dict):
    """Persist canonical fields only to datasets/users.json."""
    project_root = Path(__file__).resolve().parents[1]
    users_path = project_root / "datasets" / "users.json"

    payload = canonicalize_user_dict(as_dict_any(updated_user_obj_or_dict))

    if not users_path.exists():
        st.info("Profile updated in session. (datasets/users.json not found — skipped file save)")
        return

    try:
        with open(users_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, dict) and "users" in raw:
            users_list, wrap = raw["users"], True
        elif isinstance(raw, list):
            users_list, wrap = raw, False
        else:
            users_list, wrap = [], False

        uid = payload.get("user_id", "user")
        found = False
        for rec in users_list:
            if isinstance(rec, dict) and rec.get("user_id") == uid:
                rec.clear()
                rec.update(payload)
                found = True
                break
        if not found:
            users_list.append(payload)

        to_write = {"users": users_list} if wrap else users_list
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(to_write, f, ensure_ascii=False, indent=2)

        st.success("Profile updated and saved to datasets/users.json ✅")
    except Exception as e:
        st.warning(f"Profile updated in session, but failed to write file: {e}")

# ====================== SIDEBAR: USER PROFILE (VIEW/EDIT) ======================
with st.sidebar:
    # Pre-clear: clean input after last Enter-add (must run BEFORE widgets are created)
    if st.session_state.get("_clear_new_tag_text", False):
        st.session_state["new_tag_text"] = ""
        st.session_state["_clear_new_tag_text"] = False

    # Pre-clear: deferred cleanup when Cancel was pressed previously
    if st.session_state.get("_reset_edit_ui_pending", False):
        for k in ("edit_tags", "new_tag_text", "edit_name", "edit_group", "edit_budget"):
            st.session_state.pop(k, None)
        st.session_state["_reset_edit_ui_pending"] = False

    if "editing_profile" not in st.session_state:
        st.session_state.editing_profile = False
    if "edit_tags" not in st.session_state:
        st.session_state.edit_tags = None
    if "new_tag_text" not in st.session_state:
        st.session_state.new_tag_text = ""

    # Current user (normalized dict for display)
    u_dict = canonicalize_user_dict(as_dict_any(st.session_state["user"]))
    prefs = u_dict.get("preferred_environment", [])

    # ===== VIEW MODE =====
    if not st.session_state.editing_profile:
        st.markdown("### 👤 User Profile")
        st.markdown('<div class="gr8-card profile-card">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="row" style="gap:12px;">
              <div>
                <div class="profile-name">{u_dict.get('name','User')}</div>
                <div class="profile-sub">@{u_dict.get('user_id','user')}</div>
              </div>
            </div>
            <hr/>
            <p><b>Group Size:</b> {u_dict.get('group_size','—')}</p>
            <p><b>Budget:</b> {fmt_money(u_dict.get('budget','—'))}</p>
            """,
            unsafe_allow_html=True,
        )
        if prefs:
            chips = " ".join(f"<span class='gr8-chip'>{p}</span>" for p in prefs)
            st.markdown(f"<p><b>Preferred Environments:</b></p><div>{chips}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("✏️ Modify"):
            st.session_state.editing_profile = True
            # Initialize the tag list and clear the input
            st.session_state.edit_tags = list(prefs)
            st.session_state.new_tag_text = ""
            st.rerun()

        st.divider()
        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.switch_page("pages/login.py")

    # ===== EDIT MODE (formless; press Enter to add tags) =====
    else:
        st.markdown("### ✏️ Edit Profile")

        # Text and numeric inputs (unique keys preserve widget state)
        name_in = st.text_input("Name", value=u_dict.get("name", ""), key="edit_name")
        group_in = st.number_input(
            "Group Size", min_value=1, max_value=99, step=1,
            value=int(u_dict.get("group_size", 1)), key="edit_group"
        )
        budget_in = st.number_input(
            "Budget (per trip / per night)", min_value=0.0, step=50.0,
            value=float(u_dict.get("budget", 0.0)), key="edit_budget"
        )

        # Chip editor: show selected tags with remove (×) buttons
        st.caption("Preferred Environments")
        if st.session_state.edit_tags is None:
            st.session_state.edit_tags = list(prefs)

        # Lay out remove (×) buttons in multiple columns
        if st.session_state.edit_tags:
            cols = st.columns(min(4, len(st.session_state.edit_tags)))
            for i, tag in enumerate(st.session_state.edit_tags):
                col = cols[i % len(cols)]
                with col:
                    # Button + text inline
                    rm = st.button(f"✕ {tag}", key=f"rm_tag_{i}", help="Remove this tag")
                    if rm:
                        st.session_state.edit_tags.pop(i)
                        st.rerun()

        # Input box: Enter adds a tag chip (deferred clearing to avoid API exception)
        def _add_tag_cb():
            t = (st.session_state.get("new_tag_text") or "").strip()
            if t:
                # Deduplicate (case-insensitive)
                if t.lower() not in [x.lower() for x in st.session_state.edit_tags]:
                    st.session_state.edit_tags.append(t)
            # Mark for clearing on next run (do NOT clear here in the same run)
            st.session_state["_clear_new_tag_text"] = True

        st.text_input(
            "Add a tag and press Enter",
            key="new_tag_text",
            placeholder="e.g., beach",
            on_change=_add_tag_cb,
        )

        st.write("")  # spacing
        col1, col2 = st.columns(2)
        with col1:
            save_clicked = st.button("💾 Save")
        with col2:
            cancel_clicked = st.button("↩️ Cancel")

        if save_clicked:
            updated_dict = canonicalize_user_dict({
                **u_dict,
                "name": (name_in or "User").strip(),
                "group_size": int(st.session_state.get("edit_group", group_in)),
                "budget": float(st.session_state.get("edit_budget", budget_in)),
                "preferred_environment": st.session_state.edit_tags or [],
            })

            # Recommender-ready: return a class instance or SimpleNamespace
            updated_obj = ensure_attr_user(updated_dict)
            st.session_state["user"] = updated_obj

            # Optional: save to JSON on disk (dict payload)
            save_users_to_json(updated_obj)

            # Exit editing and force a map remount
            st.session_state.editing_profile = False
            st.session_state.map_version = st.session_state.get("map_version", 0) + 1
            st.rerun()

        if cancel_clicked:
            # Leave edit mode; defer cleanup to next run
            st.session_state.editing_profile = False
            st.session_state["_reset_edit_ui_pending"] = True
            st.rerun()

# ====================== RECOMMENDER ======================
@st.cache_resource
def get_recommender():
    from recommenders.sbert_recommender import SbertRecommender
    project_root = Path(__file__).resolve().parents[1]
    prop_file = project_root / "datasets" / "sample_property_listings.json"
    with open(prop_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    properties = data.get("properties", data if isinstance(data, list) else [])
    return SbertRecommender(properties)

recommender = get_recommender()

# Ensure the user object is attribute-accessible for the recommender
st.session_state["user"] = ensure_attr_user(st.session_state["user"])
user_obj = st.session_state["user"]

st.markdown("## 🔎 Recommended for you", help="Based on your profile preferences")

# ====================== TOP FILTERS ======================
col_topn, col_price, col_kw = st.columns([1, 1, 2], vertical_alignment="bottom")
with col_topn:
    top_n = st.slider("Top N", min_value=3, max_value=30, value=9, step=3, key="kw_topn")
with col_price:
    price_label = st.selectbox(
        "Max price per night",
        options=["No limit", "$100", "$200", "$300", "$500", "$800", "$1000"],
        index=0,
        key="kw_price",
    )
    price_cap = {
        "No limit": None,
        "$100": 100,
        "$200": 200,
        "$300": 300,
        "$500": 500,
        "$800": 800,
        "$1000": 1000,
    }[price_label]
with col_kw:
    keyword = (
        st.text_input(
            "Search keyword (based on your profile)",
            placeholder="e.g., beach, mountain, city center",
            key="kw_search",
        )
        .strip()
        .lower()
    )

# ====================== FETCH RECS & SECONDARY FILTERING ======================
try:
    raw_recs = recommender.recommend_logic(user_obj, top_n=top_n * 3)
    if not isinstance(raw_recs, list):
        raise TypeError("recommender.recommend_logic should return a list.")
except Exception as e:
    st.error(f"Recommender error: {e}")
    st.info("Tip: Clear filters (No limit / empty keyword) or inspect user fields.")
    raw_recs = []

def price_ok(p, cap):
    if cap is None:
        return True
    price = p.get("price_per_night", p.get("price"))
    try:
        return float(price) <= float(cap)
    except Exception:
        return True

def kw_ok(p, kw):
    if not kw:
        return True
    bag = []
    for k in ("name", "title", "location", "type", "description"):
        v = p.get(k)
        if isinstance(v, str):
            bag.append(v.lower())
    for k in ("features", "tags", "amenities"):
        v = p.get(k)
        if isinstance(v, list):
            bag += [str(x).lower() for x in v]
    return kw in " ".join(bag)

filtered = [p for p in raw_recs if price_ok(p, price_cap) and kw_ok(p, keyword)]
items = filtered[:top_n]

# ====================== MAP ======================
st.markdown("### 🗺️ Map of results")

def _extract_point(p):
    c = p.get("coordinates", {}) or {}
    lat = c.get("latitude", c.get("lat", p.get("latitude", p.get("lat"))))
    lng = c.get("longitude", c.get("lng", p.get("longitude", p.get("lng"))))
    if lat is None or lng is None:
        return None, None
    try:
        return float(lat), float(lng)
    except Exception:
        return None, None

# Build marker payloads (with tooltip/popup)
points = []
for i, prop in enumerate(items, start=1):
    lat, lng = _extract_point(prop)
    if lat is None or lng is None:
        continue

    title = prop.get("name") or prop.get("title") or prop.get("property_id", f"Property #{i}")
    loc = prop.get("location", "—")
    typ = prop.get("type", "—")
    price_val = prop.get("price_per_night", prop.get("price", "—"))
    try:
        price_txt = f"${float(price_val):,.0f} / night"
    except Exception:
        price_txt = f"${price_val} / night" if price_val not in (None, "—") else "—"

    chips = []
    for k in ("features", "tags", "amenities"):
        v = prop.get(k)
        if isinstance(v, list):
            chips += [str(x) for x in v][:6]
    chips_html = "".join(
        f"<span style='display:inline-block;padding:4px 10px;border-radius:9999px;background:#f3f7ff;border:1px solid #e0eaff;color:#1d4ed8;margin-right:6px;margin-top:6px;font-size:.8rem;'>{c}</span>"
        for c in chips
    )

    popup_html = f"""
    <div style="min-width:240px;">
      <div style="font-weight:700;margin-bottom:6px;">{i}. {title}</div>
      <div>📍 <b>Location:</b> {loc}</div>
      <div>🏠 <b>Type:</b> {typ}</div>
      <div>💲 <b>Price:</b> {price_txt}</div>
      <div style="margin-top:6px;">{chips_html}</div>
    </div>
    """

    points.append(
        {
            "idx": i,
            "lat": lat,
            "lng": lng,
            "title": title,
            "loc": loc,
            "typ": typ,
            "price_txt": price_txt,
            "popup": popup_html,
        }
    )

if not points:
    st.info("No coordinates available for the current results. Try clearing filters or increasing Top N.")
else:
    # Initial center: average coordinates (fit_bounds will handle final view)
    avg_lat = sum(p["lat"] for p in points) / len(points)
    avg_lng = sum(p["lng"] for p in points) / len(points)
    WORLD_BOUNDS = [[-85, -180], [85, 180]]  # Slight margin to avoid polar tile artifacts

    m = folium.Map(
        location=[avg_lat, avg_lng],   # Initial center
        zoom_start=2,                  # Initial zoom
        min_zoom=1,                    # Allow world view
        max_zoom=12,
        tiles=None,                    # Add TileLayer manually to control no_wrap
        max_bounds=True,               # Constrain panning to bounds
        max_bounds_viscosity=1.0,
        world_copy_jump=False,         # Do not duplicate world at ±180°
        prefer_canvas=True,
    )

    folium.TileLayer(
        tiles="CartoDB Positron",
        control=False,
        no_wrap=True,                 # Disable tile wrapping
        bounds=WORLD_BOUNDS,          # Limit tile rendering to these bounds
    ).add_to(m)

    # Cluster layer to handle overlapping markers
    cluster = MarkerCluster(
        options={
            "showCoverageOnHover": False,
            "zoomToBoundsOnClick": True,
            "spiderfyOnEveryZoom": False,
            "spiderfyOnMaxZoom": True,
            "disableClusteringAtZoom": 10,  # Stop clustering at zoom ≥ 10
            "maxClusterRadius": 60,         # Pixel radius for clustering
        }
    ).add_to(m)

    # Markers with numbered pins, tooltips + popups
    for order, pt in enumerate(points, start=1):
        icon = BeautifyIcon(
            number=pt["idx"],
            icon_shape="marker",
            border_color="#2b73ff",
            background_color="#2b73ff",
            text_color="#fff",
        )
        folium.Marker(
            location=[pt["lat"], pt["lng"]],
            icon=icon,
            tooltip=f"{pt['idx']}. {pt['title']}",
            popup=folium.Popup(html=pt["popup"], max_width=320),
            z_index_offset=1000 - order,
        ).add_to(cluster)

    # Render (use versioned key to force remount after profile save)
    st_folium(
        m, height=560, use_container_width=True,
        key=f"rec_map_cluster_v{st.session_state.get('map_version', 0)}"
    )
