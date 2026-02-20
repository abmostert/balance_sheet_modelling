# import the run_extraction script
from extracting_finance_data_yfinance import run_extraction

def main():
    ticker = "VOD.L"        # or inject from config/CLI/env
    period = "annual"      # or "quarterly"
    df = run_extraction(ticker, period=period, interactive=False, category_pattern_path="category_pattern.json", prefilter=True)
    # Do whatever you want with the DataFrame:
    print(df.head(20).to_string())

if __name__ == "__main__":
    main()
