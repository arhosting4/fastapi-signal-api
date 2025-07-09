# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Install system dependencies required for compiling TA-Lib from source
# These include build tools, wget for downloading, and unzip for extracting.
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download, compile, and install TA-Lib from source
# We'll download the latest stable version (0.4.0)
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed Python packages specified in requirements.txt
# This will now successfully install TA-Lib (the Python wrapper) because the C library is present.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Expose the port that the FastAPI application listens on
EXPOSE 8000

# Command to run the application using Gunicorn and Uvicorn workers
# Make sure 'app:app' correctly points to your FastAPI app instance in app.py
CMD ["gunicorn", "app:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
