from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# -------------------------------------------------
# 🧠 STEP 1: Database URL (PostgreSQL Connection)
# -------------------------------------------------
# Replace these values with your actual PostgreSQL credentials
DB_USER = "postgres"
DB_PASSWORD = "postgres"       # <-- change this
DB_HOST = "localhost"              # or your server IP
DB_PORT = "5432"                   # default PostgreSQL port
DB_NAME = "hospital"            # your database name

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# -------------------------------------------------
# 🧠 STEP 2: SQLAlchemy Engine & Session
# -------------------------------------------------
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# -------------------------------------------------
# 🧠 STEP 3: Dependency for FastAPI Routes
# -------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
