# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Expose the port Uvicorn will run on
EXPOSE 8000

# Launch FastAPI from correct module (app.py contains: app = FastAPI())
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
