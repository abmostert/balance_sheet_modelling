import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from db.db_utils import get_engine


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period-type", choices=["annual", "quarterly"], default=None)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    engine = get_engine()

    sql = """
        SELECT
            ticker,
            statement,
            period_type,
            period_end,
            canonical_key,
            category,
            value,
            source,
            retrieved_at_utc
        FROM canonical_balance_sheet
        WHERE ticker = :ticker
    """

    params = {"ticker": args.ticker, "limit": args.limit}

    if args.period_type:
        sql += " AND period_type = :period_type"
        params["period_type"] = args.period_type

    sql += """
        ORDER BY period_end DESC, canonical_key ASC
        LIMIT :limit
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    if df.empty:
        print("No rows found.")
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()