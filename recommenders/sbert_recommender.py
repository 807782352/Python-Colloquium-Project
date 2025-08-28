def recommend_properties_from_db(user, top_n=5, db_file=None, model_dir=None):
    """
    Recommend properties using precomputed embeddings in the SQLite DB, based on user preferences.
    Includes price_per_night and coordinates; filters by user budget if provided.
    """
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    import sqlite3
    import os

    # Database and model directories
    if db_file is None:
        db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "property_vector_db.sqlite"))
    if model_dir is None:
        model_dir = os.path.join(os.path.dirname(__file__), "sbert_models", "saved_model")

    # Load the SBERT model
    model = SentenceTransformer(model_dir)

    preferred_env = user.get("preferred_environment", []) or []
    user_text = "preferred_environment: " + ", ".join(preferred_env)
    user_vector = model.encode([user_text], convert_to_numpy=True).astype(np.float32)[0]

    # user's budget
    user_budget = None
    try:
        if user.get("budget") is not None:
            user_budget = float(user["budget"])
    except (TypeError, ValueError):
        user_budget = None

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    ensure_table(conn) 
    c.execute("""
        SELECT property_id, embedding, location, type, features, tags, price_per_night, lat, lng
        FROM property_embeddings
    """)
    rows = c.fetchall()
    conn.close()

    properties, embeddings = [], []
    for (property_id, embedding_blob, location, type_, features, tags, price, lat, lng) in rows:
        # budget filtering
        if user_budget is not None and price is not None:
            try:
                if float(price) > user_budget:
                    continue
            except (TypeError, ValueError):
                pass

        emb = np.frombuffer(embedding_blob, dtype=np.float32)
        properties.append({
            "property_id": property_id,
            "location": location,
            "type": type_,
            "features": features.split(",") if features else [],
            "tags": tags.split(",") if tags else [],
            "price_per_night": float(price) if price is not None else None,
            "coordinates": {
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
            }
        })
        embeddings.append(emb)

    if not embeddings:
        return []

    property_vectors = np.stack(embeddings)
    similarities = util.cos_sim(user_vector, property_vectors)[0]
    order = np.argsort(-similarities)[:top_n]

    results = []
    for i in order:
        prop = properties[i]
        results.append({
            "property_id": prop["property_id"],
            "similarity": float(similarities[i]),
            "price_per_night": prop["price_per_night"],
            "location": prop["location"],
            "type": prop["type"],
            "features": prop["features"],
            "tags": prop["tags"],
            "coordinates": prop["coordinates"],
        })
    return results


# This script loads property listings, generates embeddings, and stores them in a vector database for later querying.

from sentence_transformers import SentenceTransformer, util
import numpy as np

import json
import sqlite3
import os

BASE_DIR = os.path.dirname(__file__)
# Path to the property listings JSON file (robust to script location)
PROPERTIES_FILE = os.path.abspath(
    os.path.join(BASE_DIR, "..", "datasets", "property_listings.json")
)
# Path to save the SQLite database (always in the Vector embeddings folder)
SQLITE_DB_FILE = os.path.abspath(os.path.join(BASE_DIR, "property_vector_db.sqlite"))


MODEL_DIR = os.path.join(os.path.join(BASE_DIR, "sbert_models"), "saved_model")


################ PUBLIC FUNCTIONS ################


# Check if the embeddings table already exists; if so, exit early
def embeddings_table_exists(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='property_embeddings'"
    )
    exists = c.fetchone()
    conn.close()
    return bool(exists)


def load_model(MODEL_NAME="all-MiniLM-L6-v2"):
    """
    Load the SBERT model from local cache or download it from Hugging Face Hub.
    """
    # ensure dir exists
    os.makedirs(MODEL_DIR, exist_ok=True)
    # Check if the model directory exists and is not empty
    if os.path.exists(MODEL_DIR) and os.listdir(MODEL_DIR):
        print(f"[LOG] Load model from cache: {MODEL_DIR}")
        return SentenceTransformer(MODEL_DIR)

    # Otherwise, download the model from Hugging Face Hub
    print(f"[LOG] Download model {MODEL_NAME} and save to cache...")
    model = SentenceTransformer(MODEL_NAME)
    model.save(MODEL_DIR)
    return model


def init_embeddings_to_sqlite(model=None, db_file=SQLITE_DB_FILE):
    """
    Initialize the SQLite database with property embeddings.
    If the embeddings table already exists, exit early.
    """
    if embeddings_table_exists(db_file):
        print(f"[LOG] Embeddings table already exists in {db_file}.")
        return

    # Load properties from JSON file
    if not os.path.exists(PROPERTIES_FILE):
        raise FileNotFoundError(f"Properties file not found: {PROPERTIES_FILE}")

    with open(PROPERTIES_FILE, "r") as f:
        data = json.load(f)
    properties = data.get("properties", [])
    if not properties:
        print("[LOG] No properties found in JSON; nothing to initialize.")
        return

    # Add properties to the database
    model = model or load_model()
    add_properties(properties, model, db_file)


def ensure_table(conn):
    """
    Ensure table exists and migrate missing columns (price_per_night, lat, lng).
    """
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS property_embeddings (
            property_id TEXT PRIMARY KEY,
            embedding   BLOB,
            location    TEXT,
            type        TEXT,
            features    TEXT,
            tags        TEXT,
            price_per_night REAL,
            lat REAL,
            lng REAL
        )
        """
    )
    conn.commit()

    # # migrate: old table missing columns
    # c.execute("PRAGMA table_info(property_embeddings)")
    # cols = {row[1] for row in c.fetchall()}
    # alters = []
    # if "price_per_night" not in cols:
    #     alters.append("ALTER TABLE property_embeddings ADD COLUMN price_per_night REAL")
    # if "lat" not in cols:
    #     alters.append("ALTER TABLE property_embeddings ADD COLUMN lat REAL")
    # if "lng" not in cols:
    #     alters.append("ALTER TABLE property_embeddings ADD COLUMN lng REAL")
    # for stmt in alters:
    #     c.execute(stmt)
    # if alters:
    #     conn.commit()



def add_properties(new_props, model, db_file=SQLITE_DB_FILE):
    """
    Upsert properties including price_per_night and coordinates (lat/lng).
    """
    if isinstance(new_props, dict):
        new_props = [new_props]
    if not new_props:
        print("[LOG] No properties to add.")
        return 0

    texts = [compose_property_text(p) for p in new_props]
    embs = model.encode(texts, convert_to_numpy=True).astype(np.float32)

    rows_data = []
    for p, emb in zip(new_props, embs):
        coords = (p.get("coordinates") or {})
        lat = coords.get("lat", None)
        lng = coords.get("lng", None)
        price = p.get("price_per_night", None)

        rows_data.append((
            p["property_id"],
            emb.tobytes(),
            p.get("location", ""),
            p.get("type", ""),
            ",".join(p.get("features", []) or []),
            ",".join(p.get("tags", []) or []),
            float(price) if price is not None else None,
            float(lat) if lat is not None else None,
            float(lng) if lng is not None else None,
        ))

    conn = sqlite3.connect(db_file)
    ensure_table(conn) 
    conn.executemany(
        """
        INSERT OR REPLACE INTO property_embeddings
        (property_id, embedding, location, type, features, tags, price_per_night, lat, lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows_data,
    )
    conn.commit()
    conn.close()

    print(f"[LOG] Upserted {len(rows_data)} record(s) into {db_file}.")
    return len(rows_data)



def compose_property_text(property):
    """
    Compose property information (from dict) to a structured text for embedding (vectorization)
    location + type + features + tags.
    """
    location = str(property.get("location", "")).strip()
    type_ = str(property.get("type", "")).strip()
    features = (
        property.get("features") if isinstance(property.get("features"), list) else []
    )
    tags = property.get("tags") if isinstance(property.get("tags"), list) else []

    string = []
    if location:
        string.append(f"location: {location}")
    if type_:
        string.append(f"type: {(type_)}")
    if features:
        string.append("features: " + ", ".join(features))
    if tags:
        string.append("tags: " + ", ".join(tags))

    return " ; ".join(string)


################# SBERT RECOMMENDER CLASS ################
class SbertRecommender:
    """
    Doc Reference: https://sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html
    Video Reference: https://www.youtube.com/watch?app=desktop&v=nZ5j289WN8g
    """

    def __init__(self, properties):
        """
        Initialize the SBERT model, and load properties.
        """

        # Load a pretrained Sentence Transformer model
        self.model = load_model(MODEL_NAME="all-MiniLM-L6-v2")

        # Load properties (from dict)
        self.properties = properties

        # Compose the property texts to encode
        self.property_texts = [
            compose_property_text(property) for property in properties
        ]

        # Calculate embeddings for properties
        self.property_vectors = self.embed_to_vector(self.property_texts)

    def compose_user_text(self, user):
        """
        Compose user preferred environment to a structured text for embedding (vectorization)
        """
        preferred_env = user.preferred_environment or []
        return "preferred_environment: " + ", ".join(preferred_env)

    def embed_to_vector(self, texts):
        """
        Calculate embeddings for texts
        """
        return self.model.encode(texts, convert_to_numpy=True).astype(np.float32)

    def recommend_logic(self, user, top_n=5):
        """
        Based on the similarity between user_
        """
        user_text = self.compose_user_text(user)

        user_budget = float(user.budget)

        # Filter all properties that is under the budget
        mask_i = []
        for i, prop in enumerate(self.properties):
            if float(prop.get("price_per_night")) <= user_budget:
                mask_i.append(i)

        user_vector = self.embed_to_vector([user_text])[0]

        filtered_property_vector = self.property_vectors[mask_i]

        similarities = util.cos_sim(user_vector, filtered_property_vector)[0]

        num_properties = len(filtered_property_vector)
        top_n = min(top_n, num_properties)

        order_on_mask_i = np.argsort(-similarities)[:top_n]
        # example output: [2, 3, 1, 0], which shows the rank order based on the filtered vector (mask)

        results = []
        for i in order_on_mask_i:
            idx = mask_i[i]  # true index of property
            results.append(
                {
                    "property_id": self.properties[idx]["property_id"],
                    "similarity": float(similarities[i]),
                    "price_per_night": self.properties[idx].get("price_per_night"),
                    "location": self.properties[idx].get("location"),
                    "type": self.properties[idx].get("type"),
                    "features": self.properties[idx].get("features"),
                    "tags": self.properties[idx].get("tags"),
                    "coordinates": (self.properties[idx].get("coordinates") or {}),
                }
            )
        return results

