import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

# Make project root importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from extracting_finance_data_yfinance import run_extraction
from db.db_utils import get_engine


def canonical_wide_to_long(
    canonical_df: pd.DataFrame,
    ticker: str,
    period_type: str,
    statement: str = "balance_sheet",
    source: str = "yfinance",
) -> pd.DataFrame:
    """
    Convert canonical wide dataframe into SQL-ready long format.
    """
    df = canonical_df.copy()

    meta_cols = {"category", "canonical_key"}
    date_cols = [c for c in df.columns if c not in meta_cols]

    long_df = (
        df.reset_index(drop=True)
          .melt(
              id_vars=["canonical_key", "category"],
              value_vars=date_cols,
              var_name="period_end",
              value_name="value",
          )
    )

    long_df["ticker"] = ticker
    long_df["statement"] = statement
    long_df["period_type"] = period_type
    long_df["source"] = source
    long_df["retrieved_at_utc"] = datetime.now(timezone.utc)

    long_df["period_end"] = pd.to_datetime(long_df["period_end"], errors="coerce").dt.date
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")

    long_df = long_df.dropna(subset=["period_end", "value"])

    long_df = long_df[
        [
            "ticker",
            "statement",
            "period_type",
            "period_end",
            "canonical_key",
            "category",
            "value",
            "source",
            "retrieved_at_utc",
        ]
    ]

    long_df = long_df.drop_duplicates(
        subset=["ticker", "statement", "period_type", "period_end", "canonical_key"]
    )

    return long_df


def create_table_if_not_exists(engine) -> None:
    sql_path = PROJECT_ROOT / "sql" / "001_create_canonical_balance_sheet.sql"
    sql_text = sql_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        for stmt in sql_text.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))


def upsert_canonical(engine, canonical_long: pd.DataFrame) -> None:
    upsert_sql = text("""
        INSERT INTO canonical_balance_sheet (
            ticker,
            statement,
            period_type,
            period_end,
            canonical_key,
            category,
            value,
            source,
            retrieved_at_utc
        )
        VALUES (
            :ticker,
            :statement,
            :period_type,
            :period_end,
            :canonical_key,
            :category,
            :value,
            :source,
            :retrieved_at_utc
        )
        ON CONFLICT (ticker, statement, period_type, period_end, canonical_key)
        DO UPDATE SET
            category = EXCLUDED.category,
            value = EXCLUDED.value,
            source = EXCLUDED.source,
            retrieved_at_utc = EXCLUDED.retrieved_at_utc
    """)

    records = canonical_long.to_dict(orient="records")

    with engine.begin() as conn:
        conn.execute(upsert_sql, records)


def ingest_one_period(engine, ticker: str, period_type: str) -> int:
    result = run_extraction(
        ticker,
        period=period_type,
        mode="production",
        canonical_schema_path="canonical_schema.json",
    )

    canonical_df = result["canonical"]

    canonical_long = canonical_wide_to_long(
        canonical_df=canonical_df,
        ticker=ticker,
        period_type=period_type,
    )

    upsert_canonical(engine, canonical_long)

    print(f"Inserted/updated {len(canonical_long)} canonical rows for {ticker} ({period_type}).")
    return len(canonical_long)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period", choices=["annual", "quarterly", "both"], default="annual")
    args = parser.parse_args()

    engine = get_engine()
    create_table_if_not_exists(engine)

    total_rows = 0

    if args.period == "both":
        for p in ["annual", "quarterly"]:
            total_rows += ingest_one_period(engine, args.ticker, p)
    else:
        total_rows += ingest_one_period(engine, args.ticker, args.period)

    print(f"Done. Total rows inserted/updated: {total_rows}")


if __name__ == "__main__":
    main()