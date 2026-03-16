import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from db.db_utils import get_engine


def fetch_balance_sheet_totals(engine, ticker: str | None = None, period_type: str | None = None) -> pd.DataFrame:
    """
    Query canonical_balance_sheet and pivot the three core totals into one row per:
      ticker, statement, period_type, period_end
    """
    sql = """
        SELECT
            ticker,
            statement,
            period_type,
            period_end,
            MAX(CASE WHEN canonical_key = 'total_assets' THEN value END) AS total_assets,
            MAX(CASE WHEN canonical_key = 'total_liabilities' THEN value END) AS total_liabilities,
            MAX(CASE WHEN canonical_key = 'total_equity' THEN value END) AS total_equity
        FROM canonical_balance_sheet
        WHERE statement = 'balance_sheet'
    """

    params = {}

    if ticker:
        sql += " AND ticker = :ticker"
        params["ticker"] = ticker

    if period_type:
        sql += " AND period_type = :period_type"
        params["period_type"] = period_type

    sql += """
        GROUP BY ticker, statement, period_type, period_end
        ORDER BY ticker, period_type, period_end DESC
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    return df


def classify_balance_sheet_row(row: pd.Series) -> str:
    """
    Classify one validated balance sheet row.
    """
    a = row["total_assets"]
    l = row["total_liabilities"]
    e = row["total_equity"]
    diff_pct = row["diff_pct_assets"]

    if pd.isna(a) or pd.isna(l) or pd.isna(e):
        return "MISSING_COMPONENTS"

    if pd.isna(diff_pct):
        return "MISSING_COMPONENTS"

    abs_diff_pct = abs(diff_pct)

    if abs_diff_pct <= 0.001:
        return "PASS"
    elif abs_diff_pct <= 0.02:
        return "WARN"
    else:
        return "FAIL"


def validate_balance_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add financial validation columns and a status classification.
    """
    out = df.copy()

    out["liabilities_plus_equity"] = out["total_liabilities"] + out["total_equity"]
    out["diff"] = out["total_assets"] - out["liabilities_plus_equity"]

    out["diff_pct_assets"] = pd.NA
    mask = out["total_assets"].notna() & (out["total_assets"] != 0) & out["diff"].notna()
    out.loc[mask, "diff_pct_assets"] = out.loc[mask, "diff"] / out.loc[mask, "total_assets"]

    out["status"] = out.apply(classify_balance_sheet_row, axis=1)

    return out


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--period-type", choices=["annual", "quarterly"], default=None)
    parser.add_argument("--fail-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    engine = get_engine()

    totals_df = fetch_balance_sheet_totals(
        engine=engine,
        ticker=args.ticker,
        period_type=args.period_type,
    )

    validated_df = validate_balance_sheet(totals_df)

    if args.fail_only:
        validated_df = validated_df[validated_df["status"].isin(["WARN", "FAIL", "MISSING_COMPONENTS"])]

    if args.limit is not None:
        validated_df = validated_df.head(args.limit)

    if validated_df.empty:
        print("No rows found.")
        return

    print(validated_df.to_string(index=False))


if __name__ == "__main__":
    main()