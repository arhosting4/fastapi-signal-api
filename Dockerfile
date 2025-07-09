# Use a specific Python version as the base image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for pandas and other libraries
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
# Use uvicorn directly instead of gunicorn for simpler logging
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"] # <--- یہ لائن تبدیل کریں
