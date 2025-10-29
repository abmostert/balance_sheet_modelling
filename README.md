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
  It also has the facility to handle items that are unknown, where the user can input the categories for the line items.
  As part of identification of the line items, the program call upon another file, category_pattern.json, to check known line items, and find the appropriate snake_case equivalent.
  At the end of the programme, a pandas dataframe should be generated, that has the line items, the category it belongs to, done in snake_case, to enable further analysis.

balance_sheet.py
  This file takes line items, and then assign them to the appropriate category, and then display the balance sheet for inspection.
  This file has not yet been integrated into access_control_file.py.

category_pattern.json
  This file holds information on the various snake case equivalents to yahoo finance line items, and to what category they belong. extracting_finance_data_yfinance.py uses this file as a dictionary for line items it extracts to enable assignment.

category_pattern_original.json
  The category_pattern.json can be modified by the user via the extracting_finance_data_yfinance.py file. Therefore, this file acts as an original backup incase of problems.

requirements.txt
  This file contains all the required packages for running succesfully the files in the repository.

  
  
