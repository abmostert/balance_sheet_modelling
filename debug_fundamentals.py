import json, sys, time
import pandas as pd

def hr(title): print(f"\n=== {title} ===")

SYMS = ["BP.L", "BP"]  # LSE + ADR

def try_yfinance(sym):
    import yfinance as yf
    t = yf.Ticker(sym)
    return {
        "bs_a": t.balance_sheet,                 # annual
        "bs_q": t.quarterly_balance_sheet,       # quarterly
        "info_ok": bool(t.info or t.fast_info),  # basic quote/info
    }

def try_yahooquery(sym):
    from yahooquery import Ticker as YQT
    t = YQT(sym)
    # price() is a quick sanity check that we can reach Yahoo
    price = t.price
    try:
        bs_a = t.balance_sheet(frequency="a")
    except Exception as e:
        bs_a = f"ERR: {e}"
    try:
        bs_q = t.balance_sheet(frequency="q")
    except Exception as e:
        bs_q = f"ERR: {e}"
    return {"price_keys": list(price.keys()) if isinstance(price, dict) else type(price),
            "bs_a": bs_a, "bs_q": bs_q}

def shape(df):
    try:
        return getattr(df, "shape", None)
    except Exception:
        return None

def main():
    for s in SYMS:
        hr(f"Testing {s} with yfinance")
        yf_res = try_yfinance(s)
        print("info_ok:", yf_res["info_ok"])
        print("balance_sheet (annual) shape:", shape(yf_res["bs_a"]))
        print("balance_sheet (quarterly) shape:", shape(yf_res["bs_q"]))

        hr(f"Testing {s} with yahooquery")
        yq_res = try_yahooquery(s)
        print("price keys (connectivity check):", yq_res["price_keys"])
        if hasattr(yq_res["bs_a"], "empty"):
            print("yahooquery annual bs empty?:", yq_res["bs_a"].empty)
        else:
            print("yahooquery annual bs type:", type(yq_res["bs_a"]), yq_res["bs_a"])

        if hasattr(yq_res["bs_q"], "empty"):
            print("yahooquery quarterly bs empty?:", yq_res["bs_q"].empty)
        else:
            print("yahooquery quarterly bs type:", type(yq_res["bs_q"]), yq_res["bs_q"])

    # Raw endpoint probe: tells us if Yahoo is serving statements at all
    import requests
    for s in SYMS:
        hr(f"Raw Yahoo endpoint probe for {s}")
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{s}"
        params = {"modules": "balanceSheetHistory,balanceSheetHistoryQuarterly"}
        r = requests.get(url, params=params, timeout=15)
        print("HTTP:", r.status_code)
        try:
            payload = r.json()
            print("has result?:", bool(payload.get("quoteSummary", {}).get("result")))
            err = payload.get("quoteSummary", {}).get("error")
            if err:
                print("error:", err)
            else:
                # Show just counts so we don’t dump huge JSON
                res = payload["quoteSummary"]["result"][0]
                for k in ("balanceSheetHistory", "balanceSheetHistoryQuarterly"):
                    items = (res.get(k, {}) or {}).get("balanceSheetStatements") or []
                    print(f"{k} statements:", len(items))
        except Exception as e:
            print("JSON parse error:", e, "\nText:", r.text[:200])

if __name__ == "__main__":
    main()