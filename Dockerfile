# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# This command tells uvicorn to run on host 0.0.0.0 which is accessible
# from outside the container (necessary for Render).
# The port is now managed by Render via the RENDER_PORT environment variable.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
