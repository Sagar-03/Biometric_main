from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Update the connection URL to use MySQL
# Format: "mysql+pymysql://<username>:<password>@<host>/<database_name>"
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://admin:admin@localhost/attendance_db"

# Create the engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# Session and Base setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
