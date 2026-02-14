# Import all the necessary modules

# Import re for regex code handeling for the catergory patterns json file
import re
# Import json since json file is being used in this code
import json
# numpy and pandas necesarry for cateloging and manipulating data
import numpy as np
import pandas as pd
# Use of yfinance for getting the financial data
import yfinance as yf

from canonical_filter_balance_sheet import apply_canonical_filter

# --helper functions--
# Create a function to change balance sheet labels into snake case labels
def normalise(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')

# Create function to categorise the line item into a balance sheet section
# Function also returns the snake case equivalent
def _categorise(snake_case_label: str, category_pattern: dict) -> str:
    for cat, patterns in category_pattern.items():
        for pat in patterns:
            if re.fullmatch(pat, snake_case_label):
                return cat
    return "unknown"

# Create a function to open the json file
# Open the category_pattern.json with encoding utf-8 to obtain the snake case labels
def _load_category_pattern(path: str = "category_pattern.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_category_pattern(category_pattern: dict, path: str = "category_pattern.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(category_pattern, f, indent=4, ensure_ascii=False)
        f.write("\n")

# -- main script --
def run_extraction(ticker: str, period: str = 'annual', interactive: bool = False, category_pattern_path: str = "category_pattern.json", prefilter: bool = True) -> "pd.DataFrame":
    if period not in ("annual", "quarterly"):
        raise ValueError("Period must be 'annual' or 'quarterly'.")

    # Use real data to run the programme
    t = yf.Ticker(ticker)
    # Extract the balance sheet
    bs = t.balance_sheet if period == "annual" else t.quarterly_balance_sheet

    # guard: empty dataframe
    if bs is None or bs.empty:
        raise ValueError(f"No balance sheet returned for {ticker} ({period}).")


    # Apply the prefilter
    if prefilter:
        bs = apply_canonical_filter(bs)

    # Load the category pattern
    category_pattern = _load_category_pattern(category_pattern_path)


    # Create a relationship between line item, category and snake case
    labels = bs.index.tolist()
    snake_case_labels = {lbl: normalise(lbl) for lbl in labels}
    categories = {lbl: _categorise(snake_case_labels[lbl], category_pattern) for lbl in labels}
    cat_df = pd.DataFrame({"label": labels, "category": [categories[lbl]
                                                      for lbl in labels],
                           "snake_case": [snake_case_labels[lbl]
                                           for lbl in labels]}).set_index("label")

    # Add to the balance sheet dataframe the category and snake_case
    merged_bs = bs.join(cat_df, how="left")


    # If an unknown item is in the category label, then it means the line item needs
    # to be updated into the category pattern dictionary, or update it locally in
    # the balance sheet dataframe
    if interactive and (merged_bs['category'] == 'unknown').any():


        while True:
            # The user is given the option on what to modify
            target = merged_bs[merged_bs['category'] == 'unknown'].iloc[0]
            target_name = target.name
            print('The following line item:\n')
            print(f'{target_name}\n')
            print('has an unkown category. How do you wish to update the category?\n')
            print('1. Update the main category pattern dictionary?')
            print('2. Update the balance sheet dataframe?')
            print('3. Quit the programme?')

            user_input = input().strip()

            # The set of code to enact an update of the main category pattern dictionary
            if user_input == '1':

                # Another menu for the user to select which category to assign the unknown line item
                while True:
                    print('What category does the item belong to?\n')
                    print('1. Current Assets')
                    print('2. Non Current Assets')
                    print('3. Current Liabilities')
                    print('4. Non Current Assets')
                    print('5. Equity')
                    print('6. Totals')
                    print('7. Balance Sheet Metrics')
                    print('8. Quit\\n')
                    print('Select a number:')

                    # Creating a dictionary for the response options for the user. This setup avoids the use of a long chain of if/elif statements
                    category_assign_dict = {'1': 'current_assets', '2': 'noncurrent_assets', '3': 'current_liabilities',
                                           '4': 'noncurrent_liabilities', '5': 'equity', '6': 'totals', '7': 'balance_sheet_metrics'}

                    # Take the user input for category
                    user_input_cat_assign = input().strip()

                    # User input for category used in dictionary to assign the snake case balance sheet category
                    if user_input_cat_assign in category_assign_dict:
                        # Take regex code for the category pattern dictionary
                        user_input_regex = input('Please put in regex line. Reminder: Double every \ in regex patterns as the file is saved as a JSON (JSON escape rule).')
                        # Update the category pattern dictionary
                        cat_key = category_assign_dict[user_input_cat_assign]
                        category_pattern.setdefault(cat_key, [])
                        category_pattern[cat_key].append(user_input_regex)
                        _save_category_pattern(category_pattern, category_pattern_path)
                        # After updating patterns, re-categorise this label immediately
                        new_cat = _categorise(snake_case_labels[target_name], category_pattern)
                        merged_bs.loc[target_name, "category"] = new_cat
                        # Exit the while loop
                        break

                    # Quit the update of the main category pattern dictionary
                    elif user_input == '8':
                        break

                    # If any other accidental input, the option to retry is shown.
                    else:
                        print('Try again. Use a number only.')

            # The set of code to enact an update of the balance sheet data frame
            elif user_input == '2':

                # Another menu for the user to select which category to assign the unknown line item
                while True:
                    print('What category does the item belong to?\n')
                    print('1. Current Assets')
                    print('2. Non Current Assets')
                    print('3. Current Liabilities')
                    print('4. Non Current Liabilities')
                    print('5. Equity')
                    print('6. Totals')
                    print('7. Balance Sheet Metrics')
                    print('8. Quit\\n')
                    print('Select a number:')

                    # Creating a dictionary for the response options for the user. This setup avoids the use of a long chain of if/elif statements
                    category_assign_dict = {'1': 'current_assets', '2': 'noncurrent_assets', '3': 'current_liabilities',
                                       '4': 'noncurrent_liabilities', '5': 'equity', '6': 'totals', '7': 'balance_sheet_metrics'}

                    # Take the user input for category
                    user_input_cat_assign = input().strip()

                    # User input for category used in dictionary to assign the snake case balance sheet category
                    if user_input_cat_assign in category_assign_dict:
                        # Add the balance sheet category snake case name to the dataframe
                        merged_bs.loc[target_name, 'category'] = category_assign_dict[user_input_cat_assign]
                        # Exit the while loop
                        break

                    # Quit the update of the main category pattern dictionary
                    elif user_input == '8':
                        break

                    # If any other accidental input, the option to retry is shown.
                    else:
                        print('Try again. Use a number only.')

            # Quit the update menu
            elif user_input == '3':
                break

            # If any other accidental input, the option to retry is shown.
            else:
                print('Try again. Use a number only.')

    return merged_bs


# CLI usage: python extracting_finance_data_yfinance.py ticker label --period quarterly --interactive
if __name__ == "__main__":
    import argparse
    # instantiate class
    parser = argparse.ArgumentParser()
    # get CLI items
    parser.add_argument("ticker")
    parser.add_argument("--period", choices=["annual", "quarterly"], default="annual")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--no-prefilter", action="store_true", help="Disable canonical prefilter")
    parser.add_argument("--category-pattern-path", default="category_pattern.json")
    args = parser.parse_args()
    # run the extraction
    df = run_extraction(args.ticker, period=args.period, interactive=args.interactive, category_pattern_path=args.category_pattern_path,
        prefilter=not args.no_prefilter)

    #Print a sample of the dataframe
    print(df.head(30).to_string())
