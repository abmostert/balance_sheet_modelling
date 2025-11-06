import re
import pandas as pd

# Creating a dictionary, where a key phrase is then linked to the value, which is a canonical line item found on a balance sheet. The keys are writen in 
# regex code and should cover the numerous variations that yahoo finance supplies.
ALIASES = {
    # Assets
    r"^cash(_and)?(_cash_equivalents)?$|^cash_and_cash_equivalents$|^cashandcashequivalents$|^cash_cash_equivalents$": "cash_and_equivalents",
    r"^short(_)?term_investments$|^st_investments$|^marketable_securities$|^other_short_term_investments$": "short_term_investments",
    r"^accounts?_receivable.*$|^trade_and_other_receivables$|^receivables?$": "accounts_receivable",
    r"^inventor(y|ies)$|^inventory$": "inventory",
    r"^other_current_assets$|^prepaid.*$": "other_current_assets",
    r"^total_current_assets$|^current_assets_total$": "total_current_assets",

    r"^property_plant_equipment.*net$|^net_ppe$|^pp_e_net$|^property_plant_and_equipment_net$|^property_plant_equipment$": "ppe_net",
    r"^goodwill$": "goodwill",
    r"^intangible_assets?(?:_net)?$|^intangibles?(?:_net)?$": "intangibles",
    r"^long_term_investments$|^other_noncurrent_assets$|^other_long_term_assets$|^total_non_current_assets$": "other_noncurrent_assets",
    r"^total_assets$": "total_assets",

    # Liabilities & Equity
    r"^accounts?_payable$|^trade_payables$": "accounts_payable",
    r"^(short|current)_term_debt$|^current_portion_of_long_term_debt$|^notes_payable_current$": "short_term_debt",
    r"^other_current_liabilities$|^accrued.*$|^deferred_revenue_current$": "other_current_liabilities",
    r"^total_current_liabilities$": "total_current_liabilities",

    r"^long_term_debt$|^long_term_borrowings$|^notes_payable_long_term$": "long_term_debt",
    r"^other_noncurrent_liabilities$|^deferred_tax_liabilities.*$|^other_long_term_liabilities$|^total_non_current_liabilities$": "other_noncurrent_liabilities",
    r"^total_liabilities$": "total_liabilities",

    r"^(minority|noncontrolling)_interest$": "minority_interest",
    r"^retained_earnings$|^accumulated_deficit$": "retained_earnings",
    r"^common_stock$|^share_capital$": "common_stock",
    r"^additional_paid_in_capital$|^apic$": "additional_paid_in_capital",
    r"^treasury_stock$|^treasury_shares$": "treasury_stock",
    r"^total_(shareholders|stockholders|equity)$|^total_equity.*$|^total_stockholder_equity$": "total_equity",
    r"^total_liabilities(_and)?_equity$|^total_liabilities_and_(shareholders|stockholders|equity)$|^total_liabilities__equity$": "total_liabilities_and_equity",
}

# Creating a list of the line items in a balance sheet, in the order they usually appear.
CANONICAL_ORDER = [
    # Assets
    "cash_and_equivalents","short_term_investments","accounts_receivable","inventory","other_current_assets",
    "total_current_assets","ppe_net","goodwill","intangibles","other_noncurrent_assets","total_assets",
    # Liabilities & Equity
    "accounts_payable","short_term_debt","other_current_liabilities","total_current_liabilities",
    "long_term_debt","other_noncurrent_liabilities","total_liabilities",
    "minority_interest","retained_earnings","common_stock","additional_paid_in_capital","treasury_stock",
    "total_equity","total_liabilities_and_equity"
]

def _norm(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')

def map_row_to_canonical(label: str) -> str | None:
    s = _norm(label)
    for pat, canon in ALIASES.items():
        if re.fullmatch(pat, s):
            return canon
    return None

def apply_canonical_filter(df_raw: "pd.DataFrame") -> "pd.DataFrame":
    """
    Input: Yahoo/YF balance sheet (rows=labels, cols=periods).
    Output: A tidy DataFrame reduced to a small canonical set (rows=canonical keys),
            picking the 'best' source when multiple raw rows map to the same canonical key,
            and computing standard fallbacks for missing totals.
    """
    # Gather candidates for each canonical key
    buckets: dict[str, pd.Series] = {}
    for raw_row in df_raw.index.astype(str):
        canon = map_row_to_canonical(raw_row)
        if not canon:
            continue
        s = df_raw.loc[raw_row]
        prev = buckets.get(canon)
        # keep the series with more data points
        if prev is None or s.count() > prev.count():
            buckets[canon] = s

    tidy = pd.DataFrame(buckets).T

    # Compute fallbacks column-wise
    for col in tidy.columns:
        # total_current_assets
        if "total_current_assets" in tidy.index and pd.isna(tidy.loc["total_current_assets", col]):
            parts = ["cash_and_equivalents","short_term_investments","accounts_receivable","inventory","other_current_assets"]
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            if vals:
                tidy.loc["total_current_assets", col] = sum(vals)

        # total_assets
        if "total_assets" in tidy.index and pd.isna(tidy.loc["total_assets", col]):
            parts = ["total_current_assets","ppe_net","goodwill","intangibles","other_noncurrent_assets"]
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            if vals:
                tidy.loc["total_assets", col] = sum(vals)

        # total_current_liabilities
        if "total_current_liabilities" in tidy.index and pd.isna(tidy.loc["total_current_liabilities", col]):
            parts = ["accounts_payable","short_term_debt","other_current_liabilities"]
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            if vals:
                tidy.loc["total_current_liabilities", col] = sum(vals)

        # total_liabilities
        if "total_liabilities" in tidy.index and pd.isna(tidy.loc["total_liabilities", col]):
            parts = ["total_current_liabilities","long_term_debt","other_noncurrent_liabilities"]
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            if vals:
                tidy.loc["total_liabilities", col] = sum(vals)

        # total_equity
        if "total_equity" in tidy.index and pd.isna(tidy.loc["total_equity", col]):
            comp_parts = ["retained_earnings","common_stock","additional_paid_in_capital","treasury_stock","minority_interest"]
            vals = [tidy.loc[p, col] for p in comp_parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            if vals:
                tidy.loc["total_equity", col] = sum(vals)
            elif "total_assets" in tidy.index and "total_liabilities" in tidy.index:
                a = tidy.loc["total_assets", col]
                l = tidy.loc["total_liabilities", col]
                if pd.notna(a) and pd.notna(l):
                    tidy.loc["total_equity", col] = a - l

        # total_liabilities_and_equity
        if "total_liabilities_and_equity" in tidy.index and pd.isna(tidy.loc["total_liabilities_and_equity", col]):
            if "total_liabilities" in tidy.index and "total_equity" in tidy.index:
                L = tidy.loc["total_liabilities", col]
                E = tidy.loc["total_equity", col]
                if pd.notna(L) and pd.notna(E):
                    tidy.loc["total_liabilities_and_equity", col] = L + E

    # Reorder for readability
    tidy = tidy.reindex(CANONICAL_ORDER)
    return tidy
