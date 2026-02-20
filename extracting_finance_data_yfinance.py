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
      - unmapped raw labels
      - collisions (canonical key -> raw labels)
      - quality checks table
    """
    # 1) Unmapped + collisions
    unmapped = []
    collisions = defaultdict(list)

    for raw_label in raw_bs.index.astype(str):
        canon = map_row_to_canonical(raw_label)
        if canon is None:
            unmapped.append(
                {"raw_label": raw_label, "normalised": norm_raw_label(raw_label)}
            )
        else:
            collisions[canon].append(raw_label)

    # only collisions where >1 raw label mapped to same canon
    collisions_multi = {k: v for k, v in collisions.items() if len(v) > 1}

    # 2) Quality checks (using canonical output)
    qc = _quality_checks(canon_bs)

    return {
        "unmapped": unmapped,
        "collisions": collisions_multi,
        "quality_checks": qc,
    }

def _print_diagnostic(report: dict, max_unmapped: int = 50) -> None:
    print("\n=== MODE 2: DIAGNOSTIC / COVERAGE REPORT ===\n")

    unmapped = report["unmapped"]
    collisions = report["collisions"]
    qc: pd.DataFrame = report["quality_checks"]

    print(f"Unmapped raw labels: {len(unmapped)}")
    if unmapped:
        show = unmapped[:max_unmapped]
        df_u = pd.DataFrame(show)
        print(df_u.to_string(index=False))
        if len(unmapped) > max_unmapped:
            print(f"... ({len(unmapped) - max_unmapped} more not shown)")

    print("\nCollisions (multiple raw labels -> same canonical key):")
    if not collisions:
        print("None")
    else:
        for canon, raws in sorted(collisions.items()):
            print(f"- {canon}:")
            for r in raws:
                print(f"    {r}")

    print("\nQuality checks (per period):")
    print(qc.to_string())

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

    return merged


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