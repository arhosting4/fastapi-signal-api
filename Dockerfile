# Use a modern and stable Python runtime as a parent image
FROM python:3.9-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# --- TA-Lib C Library Installation ---
# 1. Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 2. Download and build TA-Lib from source
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib-0.4.0-src.tar.gz ta-lib/

# *** اہم تبدیلی: کمپائلر کو لائبریری کا راستہ بتائیں ***
ENV LD_LIBRARY_PATH=/usr/lib

# --- Python Dependencies ---
# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:8000"]
