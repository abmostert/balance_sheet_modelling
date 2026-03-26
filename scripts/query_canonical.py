import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from db.db_utils import get_engine


def fetch_canonical_rows(
    engine,
    ticker: str,
    period_type: str | None = None,
    canonical_key: str | None = None,
    period_end: str | None = None,
    limit: int = 100,
) -> pd.DataFrame:
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

    params = {"ticker": ticker, "limit": limit}

    if period_type:
        sql += " AND period_type = :period_type"
        params["period_type"] = period_type

    if canonical_key:
        sql += " AND canonical_key = :canonical_key"
        params["canonical_key"] = canonical_key

    if period_end:
        sql += " AND period_end = :period_end"
        params["period_end"] = period_end

    sql += """
        ORDER BY period_end DESC, period_type ASC, canonical_key ASC
        LIMIT :limit
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    return df


def fetch_canonical_summary(
    engine,
    ticker: str,
    period_type: str | None = None,
    period_end: str | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    sql = """
        SELECT
            ticker,
            statement,
            period_type,
            period_end,
            COUNT(*) AS row_count,
            MIN(retrieved_at_utc) AS first_retrieved_at_utc,
            MAX(retrieved_at_utc) AS last_retrieved_at_utc
        FROM canonical_balance_sheet
        WHERE ticker = :ticker
    """

    params = {"ticker": ticker, "limit": limit}

    if period_type:
        sql += " AND period_type = :period_type"
        params["period_type"] = period_type

    if period_end:
        sql += " AND period_end = :period_end"
        params["period_end"] = period_end

    sql += """
        GROUP BY ticker, statement, period_type, period_end
        ORDER BY period_end DESC, period_type ASC
        LIMIT :limit
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    return df


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period-type", choices=["annual", "quarterly"], default=None)
    parser.add_argument("--canonical-key", default=None)
    parser.add_argument("--period-end", default=None, help="YYYY-MM-DD")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    engine = get_engine()

    if args.summary:
        df = fetch_canonical_summary(
            engine=engine,
            ticker=args.ticker,
            period_type=args.period_type,
            period_end=args.period_end,
            limit=args.limit,
        )
    else:
        df = fetch_canonical_rows(
            engine=engine,
            ticker=args.ticker,
            period_type=args.period_type,
            canonical_key=args.canonical_key,
            period_end=args.period_end,
            limit=args.limit,
        )

    if df.empty:
        print("No rows found.")
        return

    print(df.to_string(index=False))


if __name__ == "__main__":
    main()