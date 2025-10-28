# Import all the necessary modules
import re
import numpy as np
import pandas as pd
import yfinance as yf




# Use real data to run the programme
t = yf.Ticker("BP.L")
# Extract the balance sheet
bs = t.balance_sheet
labels = bs.index.tolist()

# Create a function to change balance sheet labels into snake case labels
def normalise(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')

# Define categories and their matching snake case patterns
category_pattern = {
    "current_assets": [
        r"^cash(_and)?(_cash_equivalents)?$",
        r"^cash_and_cash_equivalents$",
        r"^other_short_term_investments$",
        r"^accounts_receivable.*",
        r"^inventory$",
        r"^total_current_assets$",
        r"^short_term_investments$",
        r"^prepaid.*",
    ],
    "noncurrent_assets": [
        r"^property_plant_equipment.*",
        r"^goodwill$",
        r"^intangible_assets.*",
        r"^long_term_investments$",
        r"^total_non_current_assets$",
    ],
    "current_liabilities": [
        r"^accounts_payable$",
        r"^short_term_debt$",
        r"^total_current_liabilities$",
        r"^accrued.*",
        r"^deferred_revenue_current$",
    ],
    "noncurrent_liabilities": [
        r"^long_term_debt$",
        r"^deferred_tax_liabilities.*",
        r"^other_long_term_liabilities$",
        r"^total_non_current_liabilities$",
    ],
    "equity": [
        r"^retained_earnings$",
        r"^common_stock$",
        r"^treasury_stock$",
        r"^accumulated_other_comprehensive_income$",
        r"^total_stockholder_equity$",
        r"^total_equity.*",
    ],
    "totals": [
        r"^total_assets$",
        r"^total_liabilities.*",
    ],
}


# Create function to categorise the line item into a balance sheet section
# Function also returns the snake case equivalent
def categorise(snake_case_label: str) -> str:

    for cat, patterns in category_pattern.items():
        for pat in patterns:
            if re.match(pat, snake_case_label):
                return cat
    return "unknown"


# Create a relationship between line item, category and snake case
snake_case_labels = {lbl: normalise(lbl) for lbl in labels}
categories = {lbl: categorise(snake_case_labels[lbl]) for lbl in labels}
cat_df = pd.DataFrame({"label": labels, "category": [categories[lbl]
                                                      for lbl in labels],
                       "snake_case": [snake_case_labels[lbl]
                                       for lbl in labels]})
cat_df = cat_df.set_index('label')

# Add to the balance sheet dataframe the category and snake_case
merged_bs = pd.merge(bs,cat_df, left_index=True, right_index=True)


# If an unknown item is in the category label, then it means the line item needs
# to be updated into the category pattern dictionary, or update it locally in
# the balance sheet dataframe
if (merged_bs['category'] == 'unknown').any():

    
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
        
        user_input = input()

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
                print('7. Quit\n')
                print('Select a number.')

                # Creating a dictionary for the response options for the user. This setup avoids the use of a long chain of if/elif statements
                category_assign_dict = {'1': 'current_assets', '2': 'noncurrent_assets', '3': 'current_liabilities',
                                       '4': 'noncurrent_liabilities', '5': 'equity', '6': 'totals'}

                # Take the user input for category
                user_input_cat_assign = input()

                # User input for category used in dictionary to assign the snake case balance sheet category
                if user_input_cat_assign in category_assign_dict:
                    # Take regex code for the category pattern dictionary
                    user_input_regex = input('Please put in regex line.')
                    # Update the category pattern dictionary
                    category_pattern[user_input_cat_assign].append(user_input_regex)
                    # Exit the while loop
                    break

                # Quit the update of the main category pattern dictionary
                elif user_input == '7':
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
                print('7. Quit\n')
                print('Select a number:1')

                 # Creating a dictionary for the response options for the user. This setup avoids the use of a long chain of if/elif statements
                category_assign_dict = {'1': 'current_assets', '2': 'noncurrent_assets', '3': 'current_liabilities',
                                       '4': 'noncurrent_liabilities', '5': 'equity', '6': 'totals'}
                
                # Take the user input for category
                user_input_cat_assign = input()

                # User input for category used in dictionary to assign the snake case balance sheet category
                if user_input in category_assign_dict:
                    # Add the balance sheet category snake case name to the dataframe
                    merged_bs.loc[target_name, 'category'] = category_assign_dict[user_input_cat_assign]
                    # Exit the while loop
                    break

                # Quit the update of the main category pattern dictionary
                elif user_input == '7':
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


