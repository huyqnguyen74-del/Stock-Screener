# Daily Stock Screener

Flags stocks where **RSI(14) < 32 AND price > 200-day moving average** as a
"BUY OPPORTUNITY," grouped into your three buckets: Top Semi Stock, Tier 2
Semi Stock, and ETFs. Runs automatically every day and shows results on a
webpage.

## What's in this folder

- `tickers.json` — your watchlist, grouped by bucket. Edit this to add/remove stocks.
- `screener.py` — pulls price history and computes RSI/200MA for every ticker.
- `.github/workflows/screener.yml` — the free scheduler that runs the script daily.
- `index.html` — the dashboard webpage.
- `results.json` — generated automatically by the script; the dashboard reads this. You don't need to create it.

## One-time setup (about 10 minutes)

1. **Create a free GitHub account** at github.com/join (just an email + password).
2. **Create a new repository**: click the `+` in the top right → "New repository." Name it something like `stock-screener`. Keep it **Public** (required for free GitHub Pages). Don't add a README/gitignore — leave it empty.
3. **Upload these files**: on your new repo's page, click "uploading an existing file," then drag in everything from this folder — including the `.github` folder with `screener.yml` inside it. Commit the changes.
4. **Turn on GitHub Pages**: go to Settings → Pages → under "Build and deployment," set Source to "Deploy from a branch," branch `main`, folder `/ (root)`. Save. GitHub will give you a URL like `https://yourusername.github.io/stock-screener/` — that's your dashboard.
5. **Run the screener once manually** to generate the first results.json: go to the "Actions" tab → click "Daily Stock Screener" → "Run workflow" → Run workflow. Wait ~1-2 minutes, then refresh your dashboard URL.
6. From here on, it runs automatically every day around 6:30am Pacific — no action needed.

## Adding stocks later

Open `tickers.json` in your GitHub repo (click the file, click the pencil ✏️ icon), add a ticker to the right bucket's list, and commit. It'll be included starting with the next scheduled run. The dashboard also has a quick "Add" box that shows a local preview immediately, with the exact snippet to paste into `tickers.json` to make it permanent.

## Notes

- Data comes from Yahoo Finance via the free `yfinance` library — no API key needed.
- GitHub Actions cron runs in UTC and doesn't shift for daylight saving, so the run time will drift by an hour between PST and PDT. Adjust the `cron` line in `screener.yml` if you want it exact year-round.
- This is a technical signal only — it doesn't know about earnings, news, or fundamentals. Treat flags as a research shortlist, not an automatic trade instruction.
