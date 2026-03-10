import sys
from pathlib import Path
from sqlalchemy import text

# allow imports from project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from db.db_utils import get_engine


def main():
    engine = get_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            row = result.fetchone()

        print("Database connection successful.")
        print("Postgres version:")
        print(row[0])

    except Exception as e:
        print("Database connection failed.")
        print(e)


if __name__ == "__main__":
    main()