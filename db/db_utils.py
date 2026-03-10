import os
from dotenv import load_dotenv
from sqlalchemy import create_engine


def get_database_url() -> str:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set.")
    return db_url


def get_engine():
    db_url = get_database_url()
    return create_engine(db_url, pool_pre_ping=True)