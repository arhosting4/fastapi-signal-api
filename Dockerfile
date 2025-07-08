# Use a specific Python version as the base image
# We'll use Python 3.11-slim-buster for a smaller image size and stability
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for pandas and other libraries
# build-essential is for compiling C extensions
# libgfortran5 is often needed for numpy/scipy related packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgfortran5 && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port your FastAPI application will run on
EXPOSE 10000

# Command to run the application
# Use gunicorn to serve the FastAPI app
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:10000"]
