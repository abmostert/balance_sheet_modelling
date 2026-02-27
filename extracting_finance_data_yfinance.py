import re
import json
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from canonical_filter_balance_sheet import (
    apply_canonical_filter,
    map_row_to_canonical,
    _norm as norm_raw_label,  # raw label normaliser used by canonical filter
)

# -----------------------
# Small helpers
# -----------------------

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _build_canonical_category_map(schema: dict) -> Tuple[Dict[str, str], List[str]]:
    """
    schema format (canonical_schema.json):
      {
        "categories": { "current_assets": ["cash_and_equivalents", ...], ... },
        "canonical_order": ["cash_and_equivalents", ...]
      }
    Returns:
      canon_to_cat: canonical_key -> category
      canonical_order: list of canonical keys in desired print order
    """
    categories = schema.get("categories", {})
    canon_to_cat: Dict[str, str] = {}
    for cat, keys in categories.items():
        for k in keys:
            canon_to_cat[k] = cat
    canonical_order = schema.get("canonical_order", [])
    return canon_to_cat, canonical_order

def _quality_checks(canon_bs: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a small per-period table with totals and identity check.
    Assumes canon_bs index includes (some of):
      total_assets, total_liabilities, total_equity, total_liabilities_and_equity
    """
    cols = list(canon_bs.columns)
    out_rows = []

    for col in cols:
        a = canon_bs.loc["total_assets", col] if "total_assets" in canon_bs.index else np.nan
        l = canon_bs.loc["total_liabilities", col] if "total_liabilities" in canon_bs.index else np.nan
        e = canon_bs.loc["total_equity", col] if "total_equity" in canon_bs.index else np.nan

        le = np.nan
        if pd.notna(l) and pd.notna(e):
            le = l + e

        diff = np.nan
        diff_pct = np.nan
        if pd.notna(a) and pd.notna(le) and a != 0:
            diff = a - le
            diff_pct = diff / a

        out_rows.append(
            {
                "period": col,
                "total_assets": a,
                "total_liabilities": l,
                "total_equity": e,
                "liab_plus_equity": le,
                "A_minus_(L+E)": diff,
                "diff_pct_of_assets": diff_pct,
            }
        )

    qc = pd.DataFrame(out_rows).set_index("period")
    return qc

def _diagnostic_report(raw_bs: pd.DataFrame, canon_bs: pd.DataFrame) -> dict:
    """
    Builds:
      - unmapped raw labels (bucketed)
      - collisions (canonical key -> raw labels)
      - mapping coverage stats
      - quality checks table
    """
    raw_labels = list(raw_bs.index.astype(str))

    unmapped = []
    collisions = defaultdict(list)

    mapped_count = 0
    for raw_label in raw_labels:
        canon = map_row_to_canonical(raw_label)
        if canon is None:
            n = norm_raw_label(raw_label)
            unmapped.append(
                {
                    "raw_label": raw_label,
                    "normalised": n,
                    "bucket": _classify_unmapped(n),
                }
            )
        else:
            mapped_count += 1
            collisions[canon].append(raw_label)

    collisions_multi = {k: v for k, v in collisions.items() if len(v) > 1}

    qc = _quality_checks(canon_bs)

    # simple "balanced" flag (any period where A and L+E both exist and diff is ~0)
    balanced_periods = 0
    checked_periods = 0
    if not qc.empty:
        for _, row in qc.iterrows():
            if pd.notna(row["total_assets"]) and pd.notna(row["liab_plus_equity"]):
                checked_periods += 1
                if abs(float(row["A_minus_(L+E)"])) < 1e-6:
                    balanced_periods += 1

    return {
        "stats": {
            "raw_rows": len(raw_labels),
            "mapped_rows": mapped_count,
            "unmapped_rows": len(unmapped),
            "mapped_pct": (mapped_count / len(raw_labels)) if raw_labels else np.nan,
            "collision_keys": len(collisions_multi),
            "periods_checked_for_identity": checked_periods,
            "periods_balanced": balanced_periods,
        },
        "unmapped": unmapped,
        "collisions": collisions_multi,
        "quality_checks": qc,
    }


def _print_diagnostic(report: dict, max_unmapped_each: int = 25) -> None:
    print("\n=== MODE 2: DIAGNOSTIC / COVERAGE REPORT ===\n")

    stats = report["stats"]
    unmapped = report["unmapped"]
    collisions = report["collisions"]
    qc: pd.DataFrame = report["quality_checks"]

    # Summary
    mapped_pct = stats["mapped_pct"]
    mapped_pct_str = f"{mapped_pct*100:.1f}%" if pd.notna(mapped_pct) else "NA"

    print("Summary:")
    print(f"- raw rows: {stats['raw_rows']}")
    print(f"- mapped to canonical: {stats['mapped_rows']} ({mapped_pct_str})")
    print(f"- unmapped: {stats['unmapped_rows']}")
    print(f"- collision canonical keys: {stats['collision_keys']}")
    print(
        f"- identity check: balanced {stats['periods_balanced']}/{stats['periods_checked_for_identity']} checked periods"
    )

    # Group unmapped by bucket
    print("\nUnmapped raw labels (grouped):")
    if not unmapped:
        print("None")
    else:
        buckets = {"possible_line_items": [], "derived_or_counts": [], "uncertain": []}
        for u in unmapped:
            buckets[u["bucket"]].append(u)

    label_map = {
        "possible_line_items": "possible_line_items (review for ALIASES)",
        "derived_or_counts": "derived_or_counts (ignore for canonical)",
        "uncertain": "uncertain (review keywords)",
    }

    for key in ["possible_line_items", "derived_or_counts", "uncertain"]:
        items = buckets[key]
        display = label_map[key]
        print(f"\n[{display}] ({len(items)})")
        if not items:
            print("  None")
            continue
        df_b = pd.DataFrame(items[:max_unmapped_each])[["raw_label", "normalised"]]
        print(df_b.to_string(index=False))
        if len(items) > max_unmapped_each:
            print(f"  ... ({len(items) - max_unmapped_each} more not shown)")


    # Collisions
    print("\nCollisions (multiple raw labels -> same canonical key):")
    if not collisions:
        print("None")
    else:
        for canon, raws in sorted(collisions.items()):
            print(f"- {canon}:")
            for r in raws:
                print(f"    {r}")

    # Quality checks
    print("\nQuality checks (per period):")
    print(qc.to_string())


def _tidy_raw_statement(raw_df: pd.DataFrame, ticker: str, period: str, statement: str) -> pd.DataFrame:
    """
    Converts raw Yahoo statement (wide) into long format suitable for SQL.
    Keeps *all* items. Adds metadata columns.
    Output columns:
      ticker, statement, period_type, period_end, raw_label, normalised, value
    """
    df = raw_df.copy()
    df.index = df.index.astype(str)

    long = (
        df.reset_index()
          .rename(columns={"index": "raw_label"})
          .melt(id_vars=["raw_label"], var_name="period_end", value_name="value")
    )

    long["ticker"] = ticker
    long["statement"] = statement
    long["period_type"] = period
    long["normalised"] = long["raw_label"].map(norm_raw_label)

    # Optional: ensure period_end is datetime if possible
    # (Yahoo columns are often Timestamp already)
    return long[["ticker", "statement", "period_type", "period_end", "raw_label", "normalised", "value"]]

def _classify_unmapped(normalised: str) -> str:
    """
    Heuristic bucket for unmapped raw labels.
    Goal: reduce noise in Mode 2 output.

    Returns one of:
      - "derived_or_counts"
      - "possible_line_items"
      - "uncertain"
    """
    s = normalised

    # Strong "derived/metric/count" indicators
    derived_keywords = [
        "net_debt", "total_debt", "working_capital", "invested_capital",
        "tangible_book_value", "net_tangible_assets", "capitalization",
        "book_value", "per_share", "number", "shares", "share_issued",
        "ordinary_shares", "treasury_shares", "market_cap",
        "depreciation",
        "gains_losses",
        "equity_adjustments",
    ]


    # Strong "balance sheet line item" indicators
    line_item_keywords = [
        "payable", "receivable", "accrued", "deferred", "lease", "tax",
        "liabilities", "assets", "borrow", "debt", "loan", "provision",
        "inventory", "goodwill", "intangible", "ppe", "property", "equipment",
        "securities", "investments", "advances", "cash",

        "deferred_tax",
        "capital_lease",
    ]


    if any(k in s for k in derived_keywords):
        return "derived_or_counts"

    if any(k in s for k in line_item_keywords):
        return "possible_line_items"

    return "uncertain"



# -----------------------
# Main entry
# -----------------------

def run_extraction(
    ticker: str,
    period: str = "annual",
    mode: str = "production",  # "production" | "diagnostic"
    canonical_schema_path: str = "canonical_schema.json",
    interactive: bool = False,  # (kept for now; used only in legacy/raw workflows)
) -> pd.DataFrame:
    """
    Mode 1 (production): Yahoo -> canonicalise -> categorise via canonical_schema.json -> return dataframe.
    Mode 2 (diagnostic): Yahoo -> coverage report (unmapped/collisions/quality checks) + also returns production df.
    """
    if period not in ("annual", "quarterly"):
        raise ValueError("period must be 'annual' or 'quarterly'")
    if mode not in ("production", "diagnostic"):
        raise ValueError("mode must be 'production' or 'diagnostic'")

    t = yf.Ticker(ticker)
    raw_bs = t.balance_sheet if period == "annual" else t.quarterly_balance_sheet

    if raw_bs is None or raw_bs.empty:
        raise ValueError(f"No balance sheet returned for {ticker} ({period}).")

    # --- Mode 1 core: canonicalise ---
    canon_bs = apply_canonical_filter(raw_bs)

    # load schema (canonical categories + order)
    schema = _load_json(canonical_schema_path)
    canon_to_cat, canonical_order = _build_canonical_category_map(schema)

    # build metadata columns
    labels = canon_bs.index.astype(str).tolist()
    cat = [canon_to_cat.get(k, "unknown") for k in labels]
    meta = pd.DataFrame(
        {"category": cat, "canonical_key": labels},
        index=labels,
    )

    # reorder for consistent printing if schema provides an order
    if canonical_order:
        canon_bs = canon_bs.reindex(canonical_order)

        # meta must follow same index
        meta = meta.reindex(canonical_order)

    merged = canon_bs.join(meta, how="left")

    # --- Mode 2: diagnostics ---
    if mode == "diagnostic":
        report = _diagnostic_report(raw_bs=raw_bs, canon_bs=canon_bs)
        _print_diagnostic(report)

    raw_long = _tidy_raw_statement(raw_bs, ticker=ticker, period=period, statement="balance_sheet")

    return {
    "canonical": merged,   # canonical wide with category + canonical_key
    "raw_wide": raw_bs,    # full Yahoo wide table
    "raw_long": raw_long,  # SQL-friendly long table (everything)
    }



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--period", choices=["annual", "quarterly"], default="annual")
    parser.add_argument("--mode", choices=["production", "diagnostic"], default="production")
    parser.add_argument("--canonical-schema-path", default="canonical_schema.json")
    args = parser.parse_args()

    df = run_extraction(
        args.ticker,
        period=args.period,
        mode=args.mode,
        canonical_schema_path=args.canonical_schema_path,
    )

    print("\n=== MODE 1 OUTPUT (canonical, categorised) ===\n")
    print(df.head(30).to_string())