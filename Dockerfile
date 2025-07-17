# Use a modern and stable Python runtime as a parent image
FROM python:3.9-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# --- کوئی TA-Lib انسٹالیشن کی ضرورت نہیں ---

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
