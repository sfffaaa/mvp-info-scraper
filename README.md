# info-scraper

Automated article scraper for `~/info/interested-raw-posts/`. Collects articles from X/Twitter, HN, Medium, and Reddit across 11 topics. Claude CLI classifies and picks the best ones daily. Every 2 days, a synthesis digest is emailed.

## How It Works

```
07:00 + 19:00  scraper.py   → buffer/ (raw articles from X, HN, Medium, Reddit)
21:00          classifier.py → Claude scores buffer → saves top 3-5/topic as .md
every 2 days   synthesizer.py → Claude synthesizes → email to sfffaaa@gmail.com
```

## Setup

**1. Install dependencies**
```bash
pip3 install -r requirements.txt
```

**2. Fill in .env**
```
TWITTER_USERNAME=your_x_username
TWITTER_PASSWORD=your_x_password
GMAIL_ADDRESS=your_sender@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

**3. Set up cron** (see cron section below)

## Topics

ai-agent, ai-product, ai-tools, crypto, knowledge-management, indie-business, web3-protocol, society, prediction-markets, business-insight, defense-ai

## Manual Article Input

Paste any article content to Claude. Claude saves it directly and updates `preferences.md`.

## Commands

```bash
python3 scraper.py --dry-run     # test scrape without writing
python3 classifier.py --dry-run  # test classify without saving
python3 synthesizer.py --dry-run # test synthesis without emailing
python3 -m pytest tests/ -v      # run all tests
```

## Cron Setup

```cron
0  7  * * *   cd /home/jaypan/explorer/mvp-info-scraper && PYTHONUNBUFFERED=1 python3 scraper.py >> logs/scraper.log 2>&1
0  19 * * *   cd /home/jaypan/explorer/mvp-info-scraper && PYTHONUNBUFFERED=1 python3 scraper.py >> logs/scraper.log 2>&1
0  21 * * *   cd /home/jaypan/explorer/mvp-info-scraper && PYTHONUNBUFFERED=1 python3 classifier.py >> logs/classifier.log 2>&1
0  9  */2 * * cd /home/jaypan/explorer/mvp-info-scraper && PYTHONUNBUFFERED=1 python3 synthesizer.py >> logs/synthesizer.log 2>&1
```

## Dev Notes

- Buffer: `buffer/<YYYY-MM-DD>/<topic>/*.json`
- Output: `~/info/interested-raw-posts/<topic>/<date>-<slug>.md`
- Logs: `logs/scraper.log`, `logs/classifier.log`, `logs/synthesizer.log`
- Dedup: `seen_urls.txt`
