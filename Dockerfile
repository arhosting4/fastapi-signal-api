# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# --- Install TA-Lib dependencies ---
# These commands update the package list and install build tools and TA-Lib development files.
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install TA-Lib from source
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# --- Python dependencies ---

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Also install TA-Lib python wrapper
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir TA-Lib

# --- Application Code ---

# Copy the rest of the application code into the container at /app
COPY . .

# Add the current directory to the PYTHONPATH
# This is the crucial line that will fix the ModuleNotFoundError
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Use gunicorn for production
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:8000"]
