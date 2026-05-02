
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta,datetime
from flask import (
    Flask, send_from_directory, g,
    request, jsonify, session
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
app.config["SECRET_KEY"] = "secret"

# ─────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db:
        db.close()
        
def init_db():
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT
        );
        """)

# ─────────────────────────────────────────────
# Serve Frontend UI
# ─────────────────────────────────────────────
@app.route("/")
def server_index():
     return send_from_directory(app.static_folder, "admin.html")
 
# ═══════════════════════════════════════════════
# Task 1 — Admin Sign Up
# ═══════════════════════════════════════════════
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()

    db = get_db()
    db.execute(
        "INSERT INTO admins (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            data["full_name"],
            data["email"],
            generate_password_hash(data["password"]),
            datetime.now().isoformat()
        )
    )
    db.commit()

    return jsonify({"message": "Signup successful"})
 
# ═══════════════════════════════════════════════
# Task 1 — Admin Login + Session
# ═══════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    db = get_db()
    user = db.execute(
        "SELECT * FROM admins WHERE email=?",
        (data["email"],)
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    session["admin_id"] = user["id"]

    return jsonify({"message": "Login success"})
 
 
 
 
 
 
if __name__ == "__main__":
    init_db()
    app.run(debug = True)