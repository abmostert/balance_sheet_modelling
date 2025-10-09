# Import all the necessary modules
import re
import numpy as np
import pandas as pd
import yfinance as yf


# Use real data to run the programme
t = yf.Ticker("BP.L")
# Extract the balance sheet
bs = t.balance_sheet  # rows = labels, cols = periods
labels = bs.index.tolist()

# Create a function to change balance sheet labels into snake case labels
def normalise(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')

# 1) Define categories and their matching snake case patterns (add as you go)
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


#Create function to categorise the line item into a balance sheet section
#Function also returns the snake case equivalent
def categorise(snake_case_label: str) -> str:
    
    for cat, patterns in category_pattern.items():
        for pat in patterns:
            if re.match(pat, snake_case_label):
                return cat
    return "unknown"


#Create a relationship between line item, category and snake case
snake_case_labels = {lbl: normalise(lbl) for lbl in labels}
categories = {lbl: categorise(snake_case_labels[lbl]) for lbl in labels}
cat_df = pd.DataFrame({"label": labels, "category": [categories[lbl] for lbl in labels], "snake_case": [snake_case_labels[lbl] for lbl in labels]})
cat_df = cat_df.set_index('label')

#Add to the balance sheet dataframe the category and snake_case
merged_bs = pd.merge(bs,cat_df, left_index=True, right_index=True)


#If an unknown item is in the category label, then it means the line item needs to be updated into the category pattern dictionary, or
#update it locally in the balance sheet dataframe
if (merged_bs['category'] == 'unknown').any():
    
    while True:
        target = merged_bs[merged_bs['category'] == 'unknown'].iloc[0]#.loc[merged_bs['category'] == 'unknown'].iloc[0]
        target_name = target.name
        print('The following line item:\n')
        print(f'{target_name}\n')
        print('has an unkown category. How do you wish to update the category?\n')
        print('1. Update the main category pattern dictionary?')
        print('2. Update the balance sheet dataframe?')
        print('3. Quit the programme?')

        user_input = input()

        if user_input == '1':
            
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

                user_input = input()

                if user_input == '1':
                    user_input = input('Please put in regex line.')
                    category_pattern['current_assets'].append(user_input)

                elif user_input == '2':
                    user_input = input('Please put in regex line.')
                    category_pattern['noncurrent_assets'].append(user_input)

                elif user_input == '3':
                    user_input = input('Please put in regex line.')
                    category_pattern['current_liabilities'].append(user_input)

                elif user_input == '4':
                    user_input = input('Please put in regex line.')
                    category_pattern['noncurrent_liabilities'].append(user_input)

                elif user_input == '5':
                    user_input = input('Please put in regex line.')
                    category_pattern['equity'].append(user_input)

                elif user_input == '6':
                    user_input = input('Please put in regex line.')
                    category_pattern['totals'].append(user_input)

                elif user_input == '7':
                    break

                else:
                    print('Try again. Use a number only.')
   

        elif user_input == '2':

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

                user_input = input()

                if user_input == '1':
                    merged_bs

                    

                elif user_input == '2':
                    user_input = input('Please put in regex line.')
                    category_pattern['noncurrent_assets'].append(user_input)

                elif user_input == '3':
                    user_input = input('Please put in regex line.')
                    category_pattern['current_liabilities'].append(user_input)

                elif user_input == '4':
                    user_input = input('Please put in regex line.')
                    category_pattern['noncurrent_liabilities'].append(user_input)

                elif user_input == '5':
                    user_input = input('Please put in regex line.')
                    category_pattern['equity'].append(user_input)

                elif user_input == '6':
                    user_input = input('Please put in regex line.')
                    category_pattern['totals'].append(user_input)

                elif user_input == '7':
                    break

                else:
                    print('Try again. Use a number only.')


        elif user_input == '3':
            break

        else:
            print('Try again. Use a number only.')

