# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Set environment variables
# - PORT: The port the application listens on within the container
# - PYTHONUNBUFFERED: Ensures output is unbuffered (helpful for logging)
ENV PORT=8080 \
    PYTHONUNBUFFERED=1

# Install any system dependencies needed for building certain Python packages
# Adjust as required (e.g., if you need SSL libraries, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user named 'appuser' with a home directory
RUN useradd --create-home --shell /bin/bash appuser

# Set the working directory to /home/appuser/app
WORKDIR /home/appuser/app

# Copy in the requirements.txt from the parent directory
# (Assuming this Dockerfile is located in 'docker/' and requirements.txt is at the project root)
COPY ../requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the 'app' directory from the parent folder into the container
COPY ../app ./app

# If your main.py is in app/main.py, no extra copy is needed. If you prefer an entry point outside:
# COPY ../app/main.py ./main.py
# (But typically you'll run uvicorn referencing app.main:app directly.)

# Change ownership of everything to the non-root user
RUN chown -R appuser:appuser /home/appuser/app

# Switch to the non-root user
USER appuser

# Expose the container's listening port (not strictly required by Cloud Run, but good documentation)
EXPOSE $PORT

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
