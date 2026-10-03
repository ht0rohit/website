# CA Daily

A static current-affairs site for banking and government exam prep (IBPS, SBI, RBI Grade B, SSC). Content comes from Press Information Bureau (PIB) English press releases, ranked by exam relevance and linked back to the source.

## Features
- Daily digest with banking/RBI items first, 30-day date strip and archive
- Topic filters, client-side search, save and mark-as-read (browser storage)
- Auto-generated daily quiz with streak counter
- Dark mode, mobile-first layout, print-to-PDF of a day's digest
- No framework, no build step, no tracking

## Run locally
```
python3 -m http.server 8000   # open http://localhost:8000
python3 scripts/fetch_pib.py  # pull the latest PIB releases into data/
python3 tests/test_fetch.py   # offline parser tests (saved PIB fixtures)
```

## How data flows
`scripts/fetch_pib.py` reads PIB's English RSS feeds, fetches each new release page, extracts ministry/date/body, categorises it (`scripts/categorize.py`) and writes `data/YYYY-MM-DD.json` plus `data/index.json`. Summaries are extractive (first sentences of the release), never paraphrased.

## Deploy (GitHub Pages)
1. Settings → Pages → Source: **GitHub Actions**.
2. Settings → Actions → General → Workflow permissions: **Read and write**.
3. `Update data` runs twice daily (07:00 and 19:00 IST); `Deploy site` publishes on push to `main` and after each data update.

## Notes
- PIB rejects user-agents that identify as bots, so the fetcher sends a plain `Mozilla/5.0` agent; it fetches sequentially with a 1 s delay.
- Categories are keyword rules and may misfile items. Edit `scripts/categorize.py` to tune them.
- Content is © Government of India/PIB; check PIB's terms before wider reuse.
