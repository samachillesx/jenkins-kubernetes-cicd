# import os
# from flask import Flask, jsonify

# app = Flask(__name__)

# APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
# APP_ENV = os.getenv("APP_ENV", "development")

# @app.get("/")
# def home():
#     return jsonify({
#         "message": "Hello from Kubernetes!",
#         "version": APP_VERSION,
#         "environment": APP_ENV
#     })

# @app.get("/health")
# def health():
#     return jsonify({"status": "healthy"}), 200

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
