import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Database URL Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logging.error("DATABASE_URL environment variable is not set. Application cannot start.")
    raise ValueError("DATABASE_URL environment variable is not set.")

# Heroku/Render use 'postgres://' which SQLAlchemy 1.4+ no longer supports.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- SQLAlchemy Engine Setup ---
try:
    engine = create_engine(DATABASE_URL)
    logging.info("Database engine created successfully.")
except Exception as e:
    logging.error(f"Failed to create database engine: {e}")
    raise

# --- Session Factory ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logging.info("Database session factory configured.")

# --- Declarative Base ---
Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session for FastAPI endpoints.
    Ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
