from extracting_finance_data_yfinance import run_extraction

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="ROCK.L")
    parser.add_argument("--period", choices=["annual", "quarterly"], default="annual")
    parser.add_argument("--mode", choices=["production", "diagnostic"], default="production")
    parser.add_argument("--canonical-schema-path", default="canonical_schema.json")
    args = parser.parse_args()

    result = run_extraction(
    args.ticker,
    period=args.period,
    mode=args.mode,
    canonical_schema_path=args.canonical_schema_path,
    )





    if args.mode == "production":
        print("\n=== ACCESS CONTROL: MODE 1 DATAFRAME (top rows) ===\n")
        print(result["canonical"].head(30).to_string())

    elif args.mode == "diagnostic":
        print(result["raw_long"].head(10).to_string(index=False))





if __name__ == "__main__":
    main()
