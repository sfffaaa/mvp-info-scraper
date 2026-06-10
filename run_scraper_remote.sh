#!/bin/bash
set -euo pipefail

HOME_ALIAS="home-pc"
HOME_DIR="~/mvp-info-scraper"
SERVER_DIR="$HOME/explorer/mvp-info-scraper"
LOG="$SERVER_DIR/logs/scraper.log"

echo "[remote-scraper] $(date '+%Y-%m-%d %H:%M:%S') Starting remote scrape..." >> "$LOG"

ssh "$HOME_ALIAS" "cd $HOME_DIR && set -a && . .env && set +a && PYTHONUNBUFFERED=1 python3 scraper.py" >> "$LOG" 2>&1

echo "[remote-scraper] $(date '+%Y-%m-%d %H:%M:%S') Syncing buffer..." >> "$LOG"
rsync -az "${HOME_ALIAS}:${HOME_DIR}/buffer/" "$SERVER_DIR/buffer/"
# NOTE: do NOT sync seen_urls.txt from home-pc — classifier maintains its own on the server

echo "[remote-scraper] $(date '+%Y-%m-%d %H:%M:%S') Done." >> "$LOG"
