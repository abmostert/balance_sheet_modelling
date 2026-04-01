import re
import pandas as pd
import numpy as np


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

    r"^(gross_)?property_plant_(and_)?equipment$|^gross_ppe$|^property_plant_and_equipment_gross$": "ppe_gross",
    r"^accumulated_?depreciation( _and_ amortization)?$|^accumulated_depreciation_and_amortization$|^accumulated_amortization$|^accum_depr.*$": "accumulated_depreciation",
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

    # Yahoo variants for totals / rollups
    r"^current_assets$": "total_current_assets",
    r"^current_liabilities$": "total_current_liabilities",

    # Total liabilities often appears as net of minority interest
    r"^total_liabilities$|^total_liabilities_net_minority_interest$": "total_liabilities",

    # Equity totals appear under multiple names
    r"^stockholders_equity$|^shareholders_equity$|^common_stock_equity$": "total_equity",

}

# Creating a list of the line items in a balance sheet, in the order they usually appear.
CANONICAL_ORDER = [
    # Assets
    "cash_and_equivalents","short_term_investments","accounts_receivable","inventory","other_current_assets",
    "total_current_assets","ppe_gross","accumulated_depreciation","ppe_net","goodwill","intangibles","other_noncurrent_assets","total_assets",
    # Liabilities & Equity
    "accounts_payable","short_term_debt","other_current_liabilities","total_current_liabilities",
    "long_term_debt","other_noncurrent_liabilities","total_liabilities",
    "minority_interest","retained_earnings","common_stock","additional_paid_in_capital","treasury_stock",
    "total_equity","total_liabilities_and_equity"
]

# Here a helper function is created, that takes any string and puts it into snake case
def _norm(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')

# Helper function for when doing cross checks on the PPE line items. This just checks that a value is present.
def _isnum(x): 
    return pd.notna(x)

# Here, the label is inserted, and the pattern is matched to the canonical list
def map_row_to_canonical(label: str) -> str | None:
    #Turn label into snake case
    s = _norm(label)
    #run through the pattern keys and see if there is a match with the label. If found, assign the
    #canonical label.
    for pat, canon in ALIASES.items():
        if re.fullmatch(pat, s):
            return canon
    return None

#The main filter function.
def apply_canonical_filter(df_raw: "pd.DataFrame") -> "pd.DataFrame":
    """
    Input: Yahoo/YF balance sheet (rows=labels, cols=periods).
    Output: A tidy DataFrame reduced to a small canonical set (rows=canonical keys),
            picking the 'best' source when multiple raw rows map to the same canonical key,
            and computing standard fallbacks for missing totals.
    """
    #Type hint to ensure the integrity of the dictionary
    buckets: dict[str, pd.Series] = {}
    # Gather candidates for each canonical key
    for raw_row in df_raw.index.astype(str):
        canon = map_row_to_canonical(raw_row)
        if not canon:
            continue
        s = df_raw.loc[raw_row]
        prev = buckets.get(canon)
        # Assume that there are multiple lines that are the same, therefore, this statement will
        # keep the series with more data points
        if prev is None or s.count() > prev.count():
            buckets[canon] = s

    # Return the tidied dataframe.
    tidy = pd.DataFrame(buckets).T

    REQUIRED_TOTALS = [
    "total_current_assets",
    "total_assets",
    "total_current_liabilities",
    "total_liabilities",
    "total_equity",
    "total_liabilities_and_equity",
    ]
    for key in REQUIRED_TOTALS:
        if key not in tidy.index:
            tidy.loc[key] = np.nan


    # Compute fallbacks column-wise
    for col in tidy.columns:

        # Here we sort out the PPE and the associated depreciation/amortization costs
        g = tidy.loc[gross_row, col] if gross_row in tidy.index else pd.NA
        a = tidy.loc[acc_row,  col] if acc_row  in tidy.index else pd.NA
        n = tidy.loc[net_row,  col] if net_row  in tidy.index else pd.NA

        # If we have gross & accum but net is NaN → compute net
        if net_row in tidy.index and _isnum(g) and _isnum(a) and pd.isna(n):
            # If accumulated depreciation is negative (common), net = gross + accum.
            tidy.loc[net_row, col] = g + a if a < 0 else g - a

        # If net & accum but gross is NaN → compute gross
        if gross_row in tidy.index and _isnum(n) and _isnum(a) and pd.isna(g):
            tidy.loc[gross_row, col] = n - a if a < 0 else n + a

        # If gross & net but accum is NaN → compute accum
        if acc_row in tidy.index and _isnum(g) and _isnum(n) and pd.isna(a):
            a_val = n - g   # if a ends negative, you'll get a negative (expected)
            tidy.loc[acc_row, col] = a_val
        
        
        # total_current_assets
        # If total current assets are not present as a value, then, calculate it from the parts that make up the total current assets
        if "total_current_assets" in tidy.index and pd.isna(tidy.loc["total_current_assets", col]):
            # List the part of the total current assests
            parts = ["cash_and_equivalents","short_term_investments","accounts_receivable","inventory","other_current_assets"]
            # Generate a list of the corresponding values to "parts" above, if parts are present
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            # If any values present, determine the total current assets
            if vals:
                tidy.loc["total_current_assets", col] = sum(vals)

        # total_assets
        # If total assets are not present as a value, then, calculate it from the parts that make up the total assets
        if "total_assets" in tidy.index and pd.isna(tidy.loc["total_assets", col]):
            # List the part of the total  assests
            parts = ["total_current_assets","ppe_net","goodwill","intangibles","other_noncurrent_assets"]
            # Generate a list of the corresponding values to "parts" above, if parts are present
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            # If any values present, determine the total assets
            if vals:
                tidy.loc["total_assets", col] = sum(vals)

        # total_current_liabilities
        # If total current liabilities are not present as a value, then, calculate it from the parts that make up the total current liabilities
        if "total_current_liabilities" in tidy.index and pd.isna(tidy.loc["total_current_liabilities", col]):
            # List the part of the total current liabilities
            parts = ["accounts_payable","short_term_debt","other_current_liabilities"]
            # Generate a list of the corresponding values to "parts" above, if parts are present
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            # If any values present, determine the total current liabilities
            if vals:
                tidy.loc["total_current_liabilities", col] = sum(vals)

        # total_liabilities
        # If total liabilities are not present as a value, then, calculate it from the parts that make up the total liabilities
        if "total_liabilities" in tidy.index and pd.isna(tidy.loc["total_liabilities", col]):
            # List the part of the total liabilities
            parts = ["total_current_liabilities","long_term_debt","other_noncurrent_liabilities"]
            # Generate a list of the corresponding values to "parts" above, if parts are present
            vals = [tidy.loc[p, col] for p in parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            # If any values present, determine the total liabilities
            if vals:
                tidy.loc["total_liabilities", col] = sum(vals)

        # total_equity
        # If total equity is not present as a value, then, calculate it from the parts that make up the total equity
        if "total_equity" in tidy.index and pd.isna(tidy.loc["total_equity", col]):
            # List the part of the total equity
            comp_parts = ["retained_earnings","common_stock","additional_paid_in_capital","treasury_stock","minority_interest"]
            # Generate a list of the corresponding values to "parts" above, if parts are present
            vals = [tidy.loc[p, col] for p in comp_parts if p in tidy.index and pd.notna(tidy.loc[p, col])]
            # If any values present, determine the total equity
            if vals:
                tidy.loc["total_equity", col] = sum(vals)
            # Fall back if it can't be computed directly, by using the accounting identidy
            elif "total_assets" in tidy.index and "total_liabilities" in tidy.index:
                a = tidy.loc["total_assets", col]
                l = tidy.loc["total_liabilities", col]
                if pd.notna(a) and pd.notna(l):
                    tidy.loc["total_equity", col] = a - l

        # total_liabilities_and_equity
        # If total liabilities and equity is not present as a value, then, calculate it from the parts that make up the total liabilities and equity
        if "total_liabilities_and_equity" in tidy.index and pd.isna(tidy.loc["total_liabilities_and_equity", col]):
            # If the above if statement is satisfied, i.e. that the row exists, then, we proceed with the second if statement. This one checks if we
            # have liabilities and equity to do the calculation
            if "total_liabilities" in tidy.index and "total_equity" in tidy.index:
                # Determine the values of equity and liability
                L = tidy.loc["total_liabilities", col]
                E = tidy.loc["total_equity", col]
                #This if statement then proceeds if both L and and E are actual values.
                if pd.notna(L) and pd.notna(E):
                    tidy.loc["total_liabilities_and_equity", col] = L + E

    # Reorder for readability
    tidy = tidy.reindex(CANONICAL_ORDER)
    return tidy
