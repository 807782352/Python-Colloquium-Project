# --- Embedding DB Check and Creation ---
def ensure_embeddings_db():
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


# main.py
# Unified launcher for CLI and UI (Streamlit) modes, using shared core.py logic.

import os
import sys
from cli import launcher

if __name__ == "__main__":
    launcher()








