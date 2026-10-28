# Use a lightweight Python 3.12 base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from generating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Send Python logs directly to the container's output
ENV PYTHONUNBUFFERED=1

# Copy the dependency list into the container
COPY requirements.txt .

# Install the Python dependencies without caching package files
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application code into the container
COPY app/ .

# Copy the HTML homepage into the working directory
COPY index.html .

# Document the port used by the Flask application
EXPOSE 5000

# Start the Flask application when the container runs
CMD ["python", "app.py"]