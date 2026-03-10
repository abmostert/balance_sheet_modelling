TICKERS = [
    "AAPL",
    "MSFT",
    "VOD.L",
]

def main():
    for ticker in TICKERS:
        try:
            print(f"Would ingest: {ticker}")
        except Exception as e:
            print(f"Failed: {ticker} -> {e}")

if __name__ == "__main__":
    main()