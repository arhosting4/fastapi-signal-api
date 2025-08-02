# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port for FastAPI (matches render.yaml startCommand)
EXPOSE 10000

# Default command to run the app (prod grade)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
