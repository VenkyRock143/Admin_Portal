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
DB_PATH  = BASE_DIR / "app.db"

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "sky"),
    static_url_path=""
)

app.config.update(
    # FIX: SECRET_KEY must come from an environment variable — never hardcoded.
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-me-in-production"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

EMAIL_RE        = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_CATEGORIES = {
    "Technology", "Business", "Design",
    "Marketing", "Data Science", "Other"
}


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
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            token      TEXT    UNIQUE,
            admin_id   INTEGER,
            expires_at TEXT,
            used       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id            INTEGER,
            name                TEXT,
            duration            TEXT,
            start_date          TEXT,
            description         TEXT,
            skills_to_gain      TEXT,
            category            TEXT,
            future_opportunities TEXT,
            max_applicants      TEXT,
            created_at          TEXT,
            updated_at          TEXT
        );
        """)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def now_utc():
    return datetime.now(timezone.utc).isoformat()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return wrapper


def validate_opportunity(data):
    required = [
        "name", "duration", "start_date", "description",
        "skills_to_gain", "category", "future_opportunities"
    ]
    for field in required:
        if not data.get(field, "").strip():
            return f"{field} is required"
    if data["category"] not in VALID_CATEGORIES:
        return "Invalid category"
    return None


def get_owned(opportunity_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM opportunities WHERE id = ? AND admin_id = ?",
        (opportunity_id, session["admin_id"])
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
    data = request.get_json(silent=True) or {}

    full_name = data.get("full_name", "").strip()
    email     = data.get("email", "").strip().lower()
    password  = data.get("password", "")
    confirm   = data.get("confirm_password", "")

    if not all([full_name, email, password, confirm]):
        return jsonify({"error": "All fields required"}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    db = get_db()

    if db.execute("SELECT id FROM admins WHERE email = ?", (email,)).fetchone():
        return jsonify({"error": "An account with this email already exists"}), 409

    db.execute(
        "INSERT INTO admins (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (full_name, email, generate_password_hash(password), now_utc())
    )
    db.commit()

    return jsonify({"message": "Signup successful"}), 201


# ═══════════════════════════════════════════════
# Task 1 — Admin Login
# ═══════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email       = data.get("email", "").strip().lower()
    password    = data.get("password", "")
    remember_me = bool(data.get("remember_me", False))

    # FIX: use .get() so missing keys never cause a 500
    if not email or not password:
        return jsonify({"error": "Invalid email or password"}), 401

    db   = get_db()
    user = db.execute("SELECT * FROM admins WHERE email = ?", (email,)).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    # FIX: honour Remember Me — permanent session lives for PERMANENT_SESSION_LIFETIME;
    # non-permanent session dies when the browser closes.
    session.permanent  = remember_me
    session["admin_id"] = user["id"]

    return jsonify({"message": "Login successful"})


# ═══════════════════════════════════════════════
# Task 1 — Logout
# ═══════════════════════════════════════════════
@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


# ═══════════════════════════════════════════════
# Task 1 — Forgot Password
# ═══════════════════════════════════════════════
@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    db   = get_db()
    user = db.execute("SELECT id FROM admins WHERE email = ?", (email,)).fetchone()

    if user:
        token  = uuid.uuid4().hex
        expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        db.execute(
            "INSERT INTO password_reset_tokens (token, admin_id, expires_at, used) VALUES (?, ?, ?, 0)",
            (token, user["id"], expiry)
        )
        db.commit()

        # In production this would be emailed; for now it is logged to the console.
        print(f"[Password Reset] token={token}  link=http://localhost:5000/reset?token={token}")

    # Always return the same message regardless of whether the email exists.
    return jsonify({"message": "If that email is registered, a reset link has been sent."})


# ═══════════════════════════════════════════════
# Task 1 — Reset Password
# ═══════════════════════════════════════════════
@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data     = request.get_json(silent=True) or {}
    token    = data.get("token", "")
    password = data.get("password", "")

    # FIX: validate the new password before accepting it
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    db  = get_db()
    row = db.execute(
        "SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0",
        (token,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Invalid or already used reset token"}), 400

    if datetime.now(timezone.utc) > datetime.fromisoformat(row["expires_at"]):
        return jsonify({"error": "Reset link has expired. Please request a new one."}), 400

    db.execute(
        "UPDATE admins SET password_hash = ? WHERE id = ?",
        (generate_password_hash(password), row["admin_id"])
    )
    db.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE id = ?",
        (row["id"],)
    )
    db.commit()

    return jsonify({"message": "Password has been reset successfully"})


# ═══════════════════════════════════════════════
# Task 2 — Create Opportunity
# ═══════════════════════════════════════════════
@app.route("/api/opportunities", methods=["POST"])
@login_required
def create_opportunity():
    data = request.get_json(silent=True) or {}

    err = validate_opportunity(data)
    if err:
        return jsonify({"error": err}), 400

    # max_applicants is optional
    max_applicants = data.get("max_applicants", "").strip()

    db = get_db()
    cursor = db.execute(
        """INSERT INTO opportunities
           (admin_id, name, duration, start_date, description,
            skills_to_gain, category, future_opportunities, max_applicants,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session["admin_id"],
            data["name"].strip(),
            data["duration"].strip(),
            data["start_date"].strip(),
            data["description"].strip(),
            data["skills_to_gain"].strip(),
            data["category"],
            data["future_opportunities"].strip(),
            max_applicants,
            now_utc(),
            now_utc(),
        )
    )
    db.commit()

    # Return the new record so the frontend can render it immediately
    new_row = db.execute(
        "SELECT * FROM opportunities WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()

    return jsonify(dict(new_row)), 201


# ═══════════════════════════════════════════════
# Task 2 — List All Opportunities
# ═══════════════════════════════════════════════
@app.route("/api/opportunities", methods=["GET"])
@login_required
def list_opportunities():   # FIX: renamed from 'all' which shadowed the Python built-in
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM opportunities WHERE admin_id = ? ORDER BY created_at DESC",
        (session["admin_id"],)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ═══════════════════════════════════════════════
# Task 2 — View Opportunity Detail
# ═══════════════════════════════════════════════
@app.route("/api/opportunities/<int:opportunity_id>", methods=["GET"])
@login_required
def get_opportunity(opportunity_id):
    row = get_owned(opportunity_id)
    if not row:
        return jsonify({"error": "Opportunity not found"}), 404
    return jsonify(dict(row))


# ═══════════════════════════════════════════════
# Task 2 — Edit Opportunity
# ═══════════════════════════════════════════════
@app.route("/api/opportunities/<int:opportunity_id>", methods=["PUT"])
@login_required
def update_opportunity(opportunity_id):
    if not get_owned(opportunity_id):
        return jsonify({"error": "Opportunity not found"}), 404

    data = request.get_json(silent=True) or {}

    err = validate_opportunity(data)
    if err:
        return jsonify({"error": err}), 400

    max_applicants = data.get("max_applicants", "").strip()

    db = get_db()
    db.execute(
        """UPDATE opportunities SET
           name = ?, duration = ?, start_date = ?, description = ?,
           skills_to_gain = ?, category = ?, future_opportunities = ?,
           max_applicants = ?, updated_at = ?
           WHERE id = ?""",
        (
            data["name"].strip(),
            data["duration"].strip(),
            data["start_date"].strip(),
            data["description"].strip(),
            data["skills_to_gain"].strip(),
            data["category"],
            data["future_opportunities"].strip(),
            max_applicants,
            now_utc(),
            opportunity_id,
        )
    )
    db.commit()

    updated = db.execute(
        "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
    ).fetchone()

    return jsonify(dict(updated))


# ═══════════════════════════════════════════════
# Task 2 — Delete Opportunity
# ═══════════════════════════════════════════════
@app.route("/api/opportunities/<int:opportunity_id>", methods=["DELETE"])
@login_required
def delete_opportunity(opportunity_id):
    if not get_owned(opportunity_id):
        return jsonify({"error": "Opportunity not found"}), 404

    db = get_db()
    db.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
    db.commit()

    return jsonify({"message": "Opportunity deleted successfully"})


# ─────────────────────────────────────────────
# Initialise DB and run
# ─────────────────────────────────────────────

init_db()

if __name__ == "__main__":
    app.run(debug=True)