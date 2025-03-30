# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Set environment variables
# - PORT: The port that the application listens on within the container
# - PYTHONUNBUFFERED: Ensures output is sent straight to terminal (no buffering)
ENV PORT=8080 \
    PYTHONUNBUFFERED=1

# (Optional) Install system dependencies needed for building certain Python packages
# e.g., gcc, libssl-dev, etc. Adjust as needed depending on your requirements.
RUN apt-get update && apt-get install -y tesseract-ocr libpoppler-cpp-dev \
    libxml2-dev libxslt-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user named 'appuser' with a home directory
RUN useradd --create-home --shell /bin/bash appuser

# Set the working directory to /home/appuser/app
WORKDIR /home/appuser/app

# Copy requirements file and install Python dependencies
# Update this path to match the location of requirements.txt in your repository
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
# Adjust the source path (project-root/app/) and destination as appropriate
COPY ./app ./app
# Example of copying entry point if needed
COPY ./app/main.py ./main.py


# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /home/appuser/app

# Switch to the non-root user
USER appuser

# Expose the port (primarily for documentation; some hosting providers rely on it)
EXPOSE $PORT

# If additional flags (e.g., Cloud SQL connections) are needed, you can mention them at runtime:
# docker run -p 8080:8080 -e DB_HOST="/cloudsql/YOUR_INSTANCE_CONNECTION_NAME" -v /cloudsql:/cloudsql --name yourcontainer yourimage
# or in Google Cloud Run/Cloud Build, configure environment variables for DB_HOST, etc.

# Start the FastAPI application using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
