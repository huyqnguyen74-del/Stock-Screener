"""
Intraday stock screener.

For every ticker in tickers.json, pulls ~1 year of daily price history
(today's row updates live during market hours), computes RSI(14) and the
350-day simple moving average, and flags a "BUY OPPORTUNITY" when RSI < 33
AND price is above the 350-day MA.

Writes results to results.json, which the dashboard (index.html) reads.

Also emails you whenever a ticker newly crosses into BUY territory. It only
suppresses repeat emails while a signal stays continuously active between
checks — if it drops out and later re-qualifies the same day, that's treated
as a fresh occurrence and you'll be emailed again. State resets each trading
day (notified.json).
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText

import pandas as pd
import yfinance as yf

RSI_PERIOD = 14
MA_PERIOD = 350
RSI_BUY_THRESHOLD = 33

NOTIFIED_FILE = "notified.json"


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
        # Pull enough calendar history to cover MA_PERIOD trading days,
        # plus a comfortable buffer — trading days are ~69% of calendar days.
        years_needed = max(1, (MA_PERIOD // 200) + 1)
        hist = yf.Ticker(ticker).history(period=f"{years_needed}y", interval="1d", auto_adjust=True)
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
            "ma": round(ma200, 2),
            "above_ma": price > ma200,
            "buy_signal": buy_signal,
        }
    except Exception as e:
        print(f"[error] {ticker}: {e}", file=sys.stderr)
        return {"ticker": ticker, "error": str(e)}


def load_notified(today: str) -> set:
    """Returns the set of tickers that were active (flagged BUY) as of the last
    check today. Resets automatically on a new day."""
    if not os.path.exists(NOTIFIED_FILE):
        return set()
    try:
        with open(NOTIFIED_FILE) as f:
            data = json.load(f)
        if data.get("date") != today:
            return set()  # new trading day, start fresh
        return set(data.get("tickers", []))
    except Exception:
        return set()


def save_notified(today: str, tickers: set):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump({"date": today, "tickers": sorted(tickers)}, f, indent=2)


def send_email(new_signals: list[dict]):
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    notify_email = os.environ.get("NOTIFY_EMAIL", gmail_address)

    if not gmail_address or not gmail_app_password:
        print("[email] Skipped: GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set", file=sys.stderr)
        return

    lines = ["New BUY OPPORTUNITY signal(s):\n"]
    for s in new_signals:
        lines.append(
            f"  {s['ticker']} ({s['category']}) — price ${s['price']:.2f}, "
            f"RSI {s['rsi']:.1f}, {MA_PERIOD}MA ${s['ma']:.2f}"
        )
    lines.append("\nDashboard: (your GitHub Pages URL)")
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"Stock Screener: {len(new_signals)} new BUY signal(s)"
    msg["From"] = gmail_address
    msg["To"] = notify_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, [notify_email], msg.as_string())
        print(f"[email] Sent alert for {len(new_signals)} new signal(s)")
    except Exception as e:
        print(f"[email] Failed to send: {e}", file=sys.stderr)


def main():
    with open("tickers.json") as f:
        categories = json.load(f)["categories"]

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    results = {
        "generated_at": now.isoformat(),
        "rsi_threshold": RSI_BUY_THRESHOLD,
        "ma_period": MA_PERIOD,
        "categories": {},
    }

    all_buy_signals = []  # every currently-active signal, across categories

    for category, tickers in categories.items():
        print(f"\n=== {category} ===")
        category_results = []
        for ticker in tickers:
            data = analyze_ticker(ticker)
            print(f"  {ticker}: {data}")
            category_results.append(data)
            if data.get("buy_signal"):
                all_buy_signals.append({**data, "category": category})
        results["categories"][category] = category_results

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nWrote results.json")

    # --- email only on tickers newly flagged since the LAST check ---
    # (not "ever flagged today" — so a signal that clears and later
    # re-qualifies the same day is treated as fresh and re-emailed)
    previously_active = load_notified(today)
    current_tickers = {s["ticker"] for s in all_buy_signals}
    new_signals = [s for s in all_buy_signals if s["ticker"] not in previously_active]

    if new_signals:
        send_email(new_signals)

    save_notified(today, current_tickers)  # this run's state becomes the baseline for the next check
    print("Done.")


if __name__ == "__main__":
    main()
