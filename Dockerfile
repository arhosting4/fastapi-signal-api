# Use a specific Python version as the base image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for pandas and other libraries
# build-essential is for compiling C extensions
# libgfortran5 is often needed for numpy/scipy related packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgfortran5 \
    wget \
    tar \
    unzip && \ # Add unzip for TA-Lib
    rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm ta-lib-0.4.0-src.tar.gz && \
    rm -rf ta-lib

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port your FastAPI application will run on
EXPOSE 10000

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
