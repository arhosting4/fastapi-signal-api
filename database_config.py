import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Database URL Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logging.error("DATABASE_URL environment variable is not set. Application cannot start.")
    raise ValueError("DATABASE_URL environment variable is not set.")

# Heroku/Render use 'postgres://' which SQLAlchemy 1.4+ no longer supports.
# This line ensures compatibility by replacing it with 'postgresql://'.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- SQLAlchemy Engine Setup ---
# The engine is the starting point for any SQLAlchemy application.
# It's the low-level object that connects to the database.
try:
    engine = create_engine(DATABASE_URL)
    logging.info("Database engine created successfully.")
except Exception as e:
    logging.error(f"Failed to create database engine: {e}")
    raise

# --- Session Factory ---
# SessionLocal is a factory for creating new Session objects.
# Each session is a unit of work for database interactions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logging.info("Database session factory configured.")

# --- Declarative Base ---
# Base is a factory for creating declarative model classes.
# All our ORM models will inherit from this class.
Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session.
    This will be used by FastAPI endpoints to inject a session.
    It ensures that the session is always closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
