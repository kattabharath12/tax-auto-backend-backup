import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Handle Railway's postgres:// vs postgresql:// issue
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite for local development
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./tax_app.db"
    print("Warning: Using SQLite database for development")

print(f"Using database: {DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL}")

try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    print("Database connection established successfully")
except Exception as e:
    print(f"Database connection error: {e}")
    raise