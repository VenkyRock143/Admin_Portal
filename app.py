
import os
from datetime import timedelta
from flask import (
    Flask, send_from_directory, g
)
from pathlib import Path


# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "app.db"

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "sky"),
    static_url_path=""
)


app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

# ─────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db:
        db.close()
        
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
        """)

# ─────────────────────────────────────────────
# Serve Frontend UI
# ─────────────────────────────────────────────
@app.route("/")
def server_index():
     return send_from_directory(app.static_folder, "admin.html")
 
if __name__ == "__main__":
    init_db()
    app.run(debug = True)