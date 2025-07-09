# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Install system dependencies required for TA-Lib
# These commands update the package list and install build tools and TA-Lib development files.
RUN apt-get update && apt-get install -y \
    build-essential \
    libta-lib-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed Python packages specified in requirements.txt
# This will now successfully install TA-Lib (the Python wrapper) because libta-lib-dev is present.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Expose the port that the FastAPI application listens on
EXPOSE 8000

# Command to run the application using Gunicorn and Uvicorn workers
# Make sure 'app:app' correctly points to your FastAPI app instance in app.py
CMD ["gunicorn", "app:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
