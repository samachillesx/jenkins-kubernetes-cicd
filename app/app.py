
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

# Initialize the Flask application.
app = Flask(__name__)

# Get the absolute path to the directory containing this file.
APP_DIR = Path(__file__).resolve().parent

# Define the expected location of index.html inside the app directory.
INDEX_PATH = APP_DIR / "index.html"

# If index.html is not inside the app directory,
# look for it in the parent directory instead.
if not INDEX_PATH.is_file():
    INDEX_PATH = APP_DIR.parent / "index.html"


# Define the homepage route.
# When a user visits "/", serve the index.html file.
@app.get("/")
def home():
    return send_from_directory(INDEX_PATH.parent, INDEX_PATH.name)


# Define the health-check endpoint.
# Kubernetes uses this endpoint to check application health.
@app.get("/health")
def health():
    # Return a JSON response and HTTP 200 (OK) status.
    return jsonify({"status": "healthy"}), 200


# Run the Flask development server only when this file
# is executed directly, not when imported as a module.
if __name__ == "__main__":
    # Listen on all network interfaces on port 5000.
    # This allows access through the container's network.
    app.run(host="0.0.0.0", port=5000)
