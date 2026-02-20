The aim of this programme is to extract financial data from yahoo finance, reproduce it for inspection, and then analyse it further.

Current State:
  At this time, the user can run the programme to extract a target company from yahoo finance, and generate a pandas dataframe. The user can also assign balance sheet line items to categories such as current assests, etc, if the initial scan is unable to designate a line item.

Next Steps:
  The extraction of line items from Yahoo finance yields a number of redundant line items that are the same, but have different labels. Therefore, the next step would be to create a filter and integrate it with the extracting_finance_data_yfinance.py file.

Files are:

access_control_file.py
  This is the central controlling file that starts and accesses all the other files.
  At this time, it only calls on the extracting_finance_data_yfinance.py file, not on any other files yet.

extracting_finance_data_yfinance.py
  This files accesses yahoo finance, extracts balance sheet data, and assigns the line items to balance sheet categories, such as current assets, equity, etc.
  Part of how it does this is it calls on a function in canonical_filter_balance_sheet.py, that does an initial filter of all line items to reduce the yahoo finance data to single, well known balance sheet line items.
  It also has the facility to handle items that are unknown, that is not captured initially by the canonical_filter_balance_sheet.py programme. The user can input the categories for the line items.
  As part of identification of the line items, the program call upon another file, category_pattern.json, to check known line items, and find the appropriate snake_case equivalent.
  At the end of the programme, a pandas dataframe should be generated, that has the line items, the category it belongs to, done in snake_case, to enable further analysis.

canonical_filter_balance_sheet.py
  This file takes data extracted from extracting_finance_data_yfinance.py, and then filters all the available line items for the balance sheet. Line items may be labeled slightly differently, but this filter will take care of the most common ones.
  With the filtering, it will then assign a snake case to the line items.

balance_sheet.py
  This file takes line items, and then assign them to the appropriate category, and then display the balance sheet for inspection.
  This file has not yet been integrated into access_control_file.py.

category_pattern.json
  This file holds information on the various snake case equivalents to yahoo finance line items, and to what category they belong. extracting_finance_data_yfinance.py uses this file as a dictionary for line items it extracts to enable assignment.

category_pattern_original.json
  The category_pattern.json can be modified by the user via the extracting_finance_data_yfinance.py file. Therefore, this file acts as an original backup incase of problems.

requirements.txt
  This file contains all the required packages for running succesfully the files in the repository.



“Two Modes”

Mode 1: Production (default)
Purpose: generate stable canonical balance-sheet data for modelling/SQL/ML.
Pipeline:

Pull Yahoo balance sheet (annual/quarterly)

Canonicalise (alias mapping + dedupe + fallback totals)

Categorise canonical keys using canonical_schema.json

Validate identity and missing criticals

Print deterministic report

Mode 2: Diagnostic / Coverage
Purpose: check whether Mode 1 is capturing Yahoo labels correctly and identify gaps.
Pipeline:

Pull Yahoo balance sheet

For each raw Yahoo row, attempt mapping → canonical key

Report unmapped rows + collisions + missing totals/identity flags
Output is a report, not production data.

An example future CLI usage will look like:

python access_control_file.py --ticker AAPL --period annual --mode production
python access_control_file.py --ticker VOD.L --period annual --mode diagnostic

"Diagnostic report contents"
1. Unmapped raw labels
Show: raw label, normalised label
Why: tells you what to add to ALIASES
2. Collisions
Show: canonical key → list of raw labels that mapped to it
Why: helps you refine regex or choose which source row is best
3. Quality checks (per period)
Show: totals present? A vs (L+E) difference?
Why: tells you whether fallback totals and identity are behaving

