from pathlib import Path
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

APP_DIR = Path(__file__).resolve().parent
INDEX_PATH = APP_DIR / "index.html"

if not INDEX_PATH.is_file():
    INDEX_PATH = APP_DIR.parent / "index.html"


@app.get("/")
def home():
    return send_from_directory(INDEX_PATH.parent, INDEX_PATH.name)


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)