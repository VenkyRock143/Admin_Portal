from flask import Flask, send_from_directory
from pathlib import Path

BASE_DIR = Path(__file__).parent

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "sky"),
    static_url_path=""
)

@app.route("/")
def server_index():
     return send_from_directory(app.static_folder, "admin.html")
 
if __name__ == "__main__":
    app.run(debug = True)