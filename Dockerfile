# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# --- THE FINAL AND CRITICAL FIX ---
# This command tells uvicorn to run on host 0.0.0.0 which is accessible
# from outside the container (necessary for Render).
# It also specifies the port 8000, which Render expects.
# The app:app part points to the 'app' variable inside the 'app.py' file.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
