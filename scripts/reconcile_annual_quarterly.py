import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from db.db_utils import get_engine


def fetch_annual_quarterly_pairs(
    engine,
    ticker: str | None = None,
    canonical_key: str | None = None,
) -> pd.DataFrame:
    """
    Fetch annual rows left-joined to quarterly rows on:
      ticker, statement, period_end, canonical_key

    This anchors the reconciliation on annual rows and checks whether a
    matching quarterly row exists for the same fiscal date and canonical key.
    """
    sql = """
        SELECT
            a.ticker,
            a.statement,
            a.period_end,
            a.canonical_key,
            a.category,
            a.value AS annual_value,
            q.value AS quarterly_value
        FROM canonical_balance_sheet a
        LEFT JOIN canonical_balance_sheet q
            ON a.ticker = q.ticker
           AND a.statement = q.statement
           AND a.period_end = q.period_end
           AND a.canonical_key = q.canonical_key
           AND q.period_type = 'quarterly'
        WHERE a.statement = 'balance_sheet'
          AND a.period_type = 'annual'
    """

    params = {}

    if ticker:
        sql += " AND a.ticker = :ticker"
        params["ticker"] = ticker

    if canonical_key:
        sql += " AND a.canonical_key = :canonical_key"
        params["canonical_key"] = canonical_key

    sql += """
        ORDER BY a.ticker, a.period_end DESC, a.canonical_key
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    return df


def classify_reconciliation_row(row: pd.Series) -> str:
    """
    Classify one annual-vs-quarterly reconciliation row.
    """
    annual_value = row["annual_value"]
    quarterly_value = row["quarterly_value"]
    diff_pct = row["diff_pct_annual"]

    if pd.isna(annual_value):
        return "MISSING_ANNUAL"

    if pd.isna(quarterly_value):
        return "MISSING_QUARTERLY"

    if pd.isna(diff_pct):
        return "MISSING_COMPARISON"

    abs_diff_pct = abs(diff_pct)

    if abs_diff_pct <= 0.001:
        return "MATCH"
    elif abs_diff_pct <= 0.02:
        return "CLOSE"
    else:
        return "MISMATCH"


def reconcile_annual_quarterly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add reconciliation columns and a status classification.
    """
    out = df.copy()

    out["diff"] = out["annual_value"] - out["quarterly_value"]
    out["diff_pct_annual"] = pd.NA

    mask = (
        out["annual_value"].notna()
        & (out["annual_value"] != 0)
        & out["quarterly_value"].notna()
        & out["diff"].notna()
    )

    out.loc[mask, "diff_pct_annual"] = (
        out.loc[mask, "diff"] / out.loc[mask, "annual_value"]
    )

    out["status"] = out.apply(classify_reconciliation_row, axis=1)

    return out


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--canonical-key", default=None)
    parser.add_argument("--fail-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    engine = get_engine()

    pairs_df = fetch_annual_quarterly_pairs(
        engine=engine,
        ticker=args.ticker,
        canonical_key=args.canonical_key,
    )

    reconciled_df = reconcile_annual_quarterly(pairs_df)

    if args.fail_only:
        reconciled_df = reconciled_df[
            reconciled_df["status"].isin(
                ["CLOSE", "MISMATCH", "MISSING_QUARTERLY", "MISSING_ANNUAL", "MISSING_COMPARISON"]
            )
        ]

    if args.limit is not None:
        reconciled_df = reconciled_df.head(args.limit)

    if reconciled_df.empty:
        print("No rows found.")
        return

    print(reconciled_df.to_string(index=False))


if __name__ == "__main__":
    main()