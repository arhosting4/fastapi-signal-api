# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# ===================================================================
# FINAL AND CORRECTED DOCKERFILE
# This sets the PYTHONPATH correctly to solve all ModuleNotFoundErrors.
# ===================================================================

# Set the PYTHONPATH environment variable
# This tells Python to look for modules in the current directory (/app)
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run your app using uvicorn
# This will now work because PYTHONPATH is set correctly.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
