# Qatar Foundation — Admin Portal

A Flask-based backend for the CertifyMe Full Stack Intern Assessment.  
The frontend UI is pre-built; this repository contains the complete backend that powers it.

---

## Tech Stack

| Layer     | Technology          |
|-----------|---------------------|
| Backend   | Python 3.10+        |
| Framework | Flask 3.x           |
| Database  | SQLite (file-based) |
| Frontend  | Pre-built Admin UI  |

---

## Project Structure

```
.
├── app.py          # Flask application (all routes + DB logic)
├── sky/            # Pre-built frontend (admin.html + assets) — do not modify
├── app.db          # SQLite database (auto-created on first run)
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set the secret key (important)

The app reads `SECRET_KEY` from the environment.  
**Never commit a real secret key to version control.**

```bash
# macOS / Linux
export SECRET_KEY="your-very-secret-random-string"

# Windows (Command Prompt)
set SECRET_KEY=your-very-secret-random-string

# Windows (PowerShell)
$env:SECRET_KEY="your-very-secret-random-string"
```

If you skip this step the app falls back to `"change-me-in-production"`, which is fine for local development only.

### 5. Run the development server

```bash
python app.py
```

The database (`app.db`) is created automatically on first run.  
Open your browser at **http://localhost:5000**.

---

## API Reference

All endpoints return JSON.  
Authenticated routes require an active session (login first).

### Authentication

| Method | Endpoint               | Auth | Description                        |
|--------|------------------------|------|------------------------------------|
| POST   | `/api/signup`          | No   | Register a new admin account       |
| POST   | `/api/login`           | No   | Log in and create a session        |
| POST   | `/api/logout`          | Yes  | Destroy the current session        |
| POST   | `/api/forgot-password` | No   | Request a password reset token     |
| POST   | `/api/reset-password`  | No   | Reset password using a valid token |

#### POST `/api/signup`
```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "password": "secret123",
  "confirm_password": "secret123"
}
```

#### POST `/api/login`
```json
{
  "email": "jane@example.com",
  "password": "secret123",
  "remember_me": true
}
```
`remember_me: true` keeps the session alive for 30 days.  
`remember_me: false` (default) ends the session when the browser closes.

#### POST `/api/forgot-password`
```json
{ "email": "jane@example.com" }
```
Always returns the same message. The reset token is printed to the server console.

#### POST `/api/reset-password`
```json
{
  "token": "<token-from-console>",
  "password": "newpassword123"
}
```

---

### Opportunities

All routes below require a valid session.

| Method | Endpoint                       | Description                     |
|--------|--------------------------------|---------------------------------|
| GET    | `/api/opportunities`           | List all opportunities (yours)  |
| POST   | `/api/opportunities`           | Create a new opportunity        |
| GET    | `/api/opportunities/<id>`      | Get full details of one         |
| PUT    | `/api/opportunities/<id>`      | Update an opportunity           |
| DELETE | `/api/opportunities/<id>`      | Delete an opportunity           |

#### POST / PUT body
```json
{
  "name": "Full Stack Developer Internship",
  "duration": "3 months",
  "start_date": "2025-08-01",
  "description": "Work on real-world projects...",
  "skills_to_gain": "React, Flask, PostgreSQL",
  "category": "Technology",
  "future_opportunities": "Full-time offer for top performers",
  "max_applicants": "50"
}
```

Valid categories: `Technology`, `Business`, `Design`, `Marketing`, `Data Science`, `Other`  
`max_applicants` is optional. All other fields are required.

---

## Key Design Decisions

- **Session security** — `SECRET_KEY` is read from the environment, never hardcoded.
- **Remember Me** — `session.permanent` is set based on the `remember_me` flag in the login payload.
- **Admin isolation** — every opportunity query filters by `admin_id = session["admin_id"]`, so admins can only see and modify their own data.
- **Ownership enforcement** — PUT and DELETE routes call `get_owned()` which checks both the record ID and the session's `admin_id` before proceeding.
- **No local storage** — all data lives in SQLite; the frontend fetches it fresh on every load.
- **DB initialisation** — `init_db()` is called at module level so it runs under any WSGI server, not just `python app.py`.
