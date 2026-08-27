"""
Daily stock screener.

For every ticker in tickers.json, pulls ~1 year of daily price history,
computes RSI(14) and the 200-day simple moving average, and flags a
"BUY OPPORTUNITY" when RSI < 32 AND price is above the 200-day MA.

Writes results to results.json, which the dashboard (index.html) reads.
"""

import json
import sys
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

RSI_PERIOD = 14
MA_PERIOD = 200
RSI_BUY_THRESHOLD = 32


def compute_rsi(closes: pd.Series, period: int = RSI_PERIOD) -> float:
    """Wilder's RSI, returns the most recent value."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def analyze_ticker(ticker: str) -> dict | None:
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
        if hist.empty or len(hist) < MA_PERIOD:
            print(f"[skip] {ticker}: not enough history ({len(hist)} rows)")
            return {"ticker": ticker, "error": "insufficient_history"}

        closes = hist["Close"]
        price = float(closes.iloc[-1])
        ma200 = float(closes.rolling(MA_PERIOD).mean().iloc[-1])
        rsi = compute_rsi(closes)

        buy_signal = (rsi < RSI_BUY_THRESHOLD) and (price > ma200)

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "ma200": round(ma200, 2),
            "above_200ma": price > ma200,
            "buy_signal": buy_signal,
        }
    except Exception as e:
        print(f"[error] {ticker}: {e}", file=sys.stderr)
        return {"ticker": ticker, "error": str(e)}


def main():
    with open("tickers.json") as f:
        categories = json.load(f)["categories"]

    results = {"generated_at": datetime.now(timezone.utc).isoformat(), "categories": {}}

    for category, tickers in categories.items():
        print(f"\n=== {category} ===")
        category_results = []
        for ticker in tickers:
            data = analyze_ticker(ticker)
            print(f"  {ticker}: {data}")
            category_results.append(data)
        results["categories"][category] = category_results

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nDone. Wrote results.json")


if __name__ == "__main__":
    main()
