
import os
from datetime import timedelta
from flask import Flask, send_from_directory
from pathlib import Path

BASE_DIR = Path(__file__).parent

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "sky"),
    static_url_path=""
)

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

# ─────────────────────────────────────────────
# Serve Frontend UI
# ─────────────────────────────────────────────
@app.route("/")
def server_index():
     return send_from_directory(app.static_folder, "admin.html")
 
if __name__ == "__main__":
    app.run(debug = True)