
import os
import sqlite3
import uuid
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
           CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            name TEXT,
            category TEXT
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
 
 # ═══════════════════════════════════════════════
# Task 1 — Forgot Password
# ═══════════════════════════════════════════════

@app.route("/api/forgot-password", methods=["POST"])
def forgot():
    data = request.get_json()
    token = uuid.uuid4().hex
    print("Reset token:", token)

    return jsonify({"message": "If email exists, reset link sent"})
 
# =========================
# OPPORTUNITIES
# =========================

# ═══════════════════════════════════════════════
# Task 2 — Add a New Opportunity
# ═══════════════════════════════════════════════

@app.route("/api/opportunities", methods=["POST"])
def create_opportunity():
    data = request.get_json()

    db = get_db()
    db.execute(
        "INSERT INTO opportunities (admin_id, name, category) VALUES (?, ?, ?)",
        (session["admin_id"], data["name"], data["category"])
    )
    db.commit()

    return jsonify({"message": "Created"})

# ═══════════════════════════════════════════════
# Task 2 — View All Opportunities
# ═══════════════════════════════════════════════
@app.route("/api/opportunities", methods=["GET"])
def get_all():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM opportunities WHERE admin_id=?",
        (session["admin_id"],)
    ).fetchall()

    return jsonify([dict(r) for r in rows])
# ═══════════════════════════════════════════════
# Task 2 — View Opportunity Details
# ═══════════════════════════════════════════════
@app.route("/api/opportunities/<int:id>", methods=["GET"])
def get_one(id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM opportunities WHERE id=? AND admin_id=?",
        (id, session["admin_id"])
    ).fetchone()

    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify(dict(row))
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
if __name__ == "__main__":
    init_db()
    app.run(debug = True)