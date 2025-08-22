# This script loads property listings, generates embeddings, and stores them in a vector database for later querying.

from sentence_transformers import SentenceTransformer, util
import numpy as np

import json
import sqlite3
import os

BASE_DIR = os.path.dirname(__file__)
# Path to the property listings JSON file (robust to script location)
PROPERTIES_FILE = os.path.abspath(
    os.path.join(BASE_DIR, "..", "datasets", "sample_property_listings.json")
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
    Ensure the property_embeddings table exists in the SQLite database.
    Otherwise, create it.
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
            tags        TEXT
        )
    """
    )
    conn.commit()


def add_properties(new_props, model, db_file=SQLITE_DB_FILE):
    """
    Generic function to add new properties (or single property) to the SQLite database.
    new_prop: dict, e.g. {"property_id": "P100", "location": "Toronto", "type": "Apartment", ...}
    return: number of records added
    """
    # 1. Generalize new_props to a list of dicts
    if isinstance(new_props, dict):
        # Single property dict
        new_props = [new_props]

    if not new_props:
        # No properties to add
        print("[LOG] No properties to add.")
        return 0

    # 2. Batch create embeddings
    texts = [compose_property_text(p) for p in new_props]

    # use convert_to_numpy=True to get numpy array directly, convert to float32 for SQLite BLOB storage
    # otherwise it will be torch.Tensor (which is not serializable)
    embs = model.encode(texts, convert_to_numpy=True).astype(np.float32)

    # 3. Create rows_data
    rows_data = [
        (
            p["property_id"],
            emb.tobytes(),
            p.get("location", ""),
            p.get("type", ""),
            ",".join(p.get("features", []) or []),
            ",".join(p.get("tags", []) or []),
        )
        for p, emb in zip(new_props, embs)
    ]

    # 4. Batch insert into database
    conn = sqlite3.connect(db_file)
    ensure_table(conn)
    conn.executemany(
        """
        INSERT OR REPLACE INTO property_embeddings
        (property_id, embedding, location, type, features, tags)
        VALUES (?, ?, ?, ?, ?, ?)
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

        # Filter further based on availability (date range)
        from utils.utils import parse_date
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # Today's date in Toronto timezone
        tz = ZoneInfo("America/Toronto")
        today = datetime.now(tz).date()
        period_days = int(getattr(user, "period", 0) or 0)

        # Filter all properties that is under the budget
        mask_i = []
        for i, prop in enumerate(self.properties):
            # Price filtering
            try:
                price_ok = float(prop.get("price_per_night")) <= user_budget
            except Exception:
                price_ok = False

            # Filter periods: period_days <= (ending_date - max(today, starting_date)).days
            try:
                start_d = parse_date(prop.get("starting_date"))  # format: YYYY-MM-DD
                end_d = parse_date(prop.get("ending_date"))

                earliest_start = max(today, start_d)  # if starting date is in the past, use today
                available_days = (end_d - earliest_start).days

                availability_ok = available_days >= period_days
            except Exception:
                availability_ok = False

            if price_ok and availability_ok:
                mask_i.append(i)

        if not mask_i:
            return []

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
                    "price_per_night": self.properties[idx]["price_per_night"],
                    "location": self.properties[idx]["location"],
                    "type": self.properties[idx]["type"],
                    "features": self.properties[idx]["features"],
                    "tags": self.properties[idx]["tags"],
                    "starting_date": self.properties[idx]["starting_date"],
                    "ending_date": self.properties[idx]["ending_date"],
                    "coordinates": self.properties[idx]["coordinates"],
                }
            )
        return results


################## Examples ################
if __name__ == "__main__":
    with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    properties = data.get("properties", [])

    user = {
        "user_id": "u001",
        "preferred_environment": ["Europe", "Ocean", "Luxury"],
        "budget": "500",
    }

    # User.from_dict(user)

    init_embeddings_to_sqlite()

    recommender = SbertRecommender(properties)
    results = recommender.recommend_logic(user, top_n=5)
    for r in results:
        print(r)
