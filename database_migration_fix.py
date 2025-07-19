# filename: database_migration_fix.py
# یہ فائل database schema کو force update کرنے کے لیے ہے

from sqlalchemy import create_engine, text, MetaData
import os

def fix_database_schema():
    """
    یہ function existing database tables کو drop کرکے نئے schema کے ساتھ recreate کرتا ہے
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # پہلے existing tables کو drop کریں
            print("--- Dropping existing tables... ---")
            connection.execute(text("DROP TABLE IF EXISTS completed_trades CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS active_trades CASCADE;"))
            connection.commit()
            print("--- Existing tables dropped successfully. ---")
            
            # اب نئے tables بنائیں
            print("--- Creating new tables with correct schema... ---")
            from models import create_db_and_tables
            create_db_and_tables()
            print("--- New tables created successfully. ---")
            
    except Exception as e:
        print(f"--- ERROR in database migration: {e} ---")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("--- Database migration completed successfully! ---")
    else:
        print("--- Database migration failed! ---")
