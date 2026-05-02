
import os
import sqlite3
import uuid
import re
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime, timezone
from flask import (
    Flask, send_from_directory, g,
    request, jsonify, session
)
from pathlib import Path
from functools import wraps


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
    SECRET_KEY="dev-secret",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_CATEGORIES = {"Technology","Business","Design","Marketing","Data Science","Other"}

# ─────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
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
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            admin_id INTEGER,
            expires_at TEXT,
            used INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            name TEXT,
            duration TEXT,
            start_date TEXT,
            description TEXT,
            skills_to_gain TEXT,
            category TEXT,
            future_opportunities TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def now():
    return datetime.now(timezone.utc).isoformat()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return wrapper

def validate_opportunity(data):
    required = ["name","duration","start_date","description","skills_to_gain","category","future_opportunities"]
    for f in required:
        if not data.get(f):
            return f"{f} is required"
    if data["category"] not in VALID_CATEGORIES:
        return "Invalid category"
    return None

def get_owned(id):
    db = get_db()
    return db.execute(
        "SELECT * FROM opportunities WHERE id=? AND admin_id=?",
        (id, session["admin_id"])
    ).fetchone()

# ─────────────────────────────────────────────
# Serve Frontend UI
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "admin.html")

# ═══════════════════════════════════════════════
# Task 1 — Admin Sign Up
# ═══════════════════════════════════════════════
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()

    full_name = data.get("full_name","").strip()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    confirm = data.get("confirm_password","")

    if not all([full_name,email,password,confirm]):
        return jsonify({"error":"All fields required"}),400

    if not EMAIL_RE.match(email):
        return jsonify({"error":"Invalid email"}),400

    if len(password)<8:
        return jsonify({"error":"Password must be 8+ chars"}),400

    if password!=confirm:
        return jsonify({"error":"Passwords mismatch"}),400

    db=get_db()

    if db.execute("SELECT id FROM admins WHERE email=?",(email,)).fetchone():
        return jsonify({"error":"Email exists"}),409

    db.execute(
        "INSERT INTO admins VALUES (NULL,?,?,?,?)",
        (full_name,email,generate_password_hash(password),now())
    )
    db.commit()

    return jsonify({"message":"Signup successful"})
# ═══════════════════════════════════════════════
# Task 1 — Admin Login + Session & Logout
# ═══════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def login():
    data=request.get_json()

    db=get_db()
    user=db.execute("SELECT * FROM admins WHERE email=?",(data["email"],)).fetchone()

    if not user or not check_password_hash(user["password_hash"],data["password"]):
        return jsonify({"error":"Invalid credentials"}),401

    session["admin_id"]=user["id"]
    return jsonify({"message":"Login success"})

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"message":"Logged out"})
 
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
# ═══════════════════════════════════════════════
# Task 2 — Edit an Opportunity
# ═══════════════════════════════════════════════
@app.route("/api/opportunities/<int:id>", methods=["PUT"])
def update(id):
    data = request.get_json()

    db = get_db()
    db.execute(
        "UPDATE opportunities SET name=?, category=? WHERE id=?",
        (data["name"], data["category"], id)
    )
    db.commit()

    return jsonify({"message": "Updated"})
 
# ═══════════════════════════════════════════════
# Task 2 — Delete an Opportunity
# ═══════════════════════════════════════════════ 
@app.route("/api/opportunities/<int:id>", methods=["DELETE"])
def delete(id):
    db = get_db()
    db.execute("DELETE FROM opportunities WHERE id=?", (id,))
    db.commit()

    return jsonify({"message": "Deleted"})
 
if __name__ == "__main__":
    init_db()
    app.run(debug = True)