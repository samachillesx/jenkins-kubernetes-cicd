import os
from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_ENV = os.getenv("APP_ENV", "development")


@app.get("/")
def home():
    return jsonify({
        "message": "Hello from Kubernetes!",
        "version": APP_VERSION,
        "environment": APP_ENV
    })


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)