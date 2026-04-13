#!/usr/bin/env python3
"""
Synthesizer: generates a synthesis report from recent articles and emails it.
Run every 2 days at 09:00 via cron.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import Settings
from email_utils import send_email, send_failure_email

CONFIG_PATH = Path(__file__).parent / "config.yaml"
ENV_PATH = Path(__file__).parent / ".env"
DRY_RUN = "--dry-run" in sys.argv


def load_recent_articles(output_dir: Path, since_date: str) -> list[dict]:
    articles = []
    for topic_dir in output_dir.iterdir():
        if not topic_dir.is_dir() or topic_dir.name == "synthesis":
            continue
        for md_file in topic_dir.glob("*.md"):
            file_date = md_file.name[:10]
            if file_date >= since_date:
                text = md_file.read_text(encoding="utf-8")
                title = text.split("\n")[0].lstrip("# ").strip()
                articles.append({
                    "title": title,
                    "topic": topic_dir.name,
                    "date": file_date,
                    "content": text[:1500],
                    "path": str(md_file),
                })
    return articles


def format_synthesis_email(report_text: str, article_count: int, date_str: str) -> str:
    # Convert markdown to HTML
    lines = []
    for line in report_text.split("\n"):
        if line.startswith("## "):
            lines.append(f'<h3 style="color:#333;border-bottom:1px solid #eee;padding-bottom:4px;">{line[3:]}</h3>')
        elif line.startswith("# "):
            lines.append(f'<h2 style="color:#222;">{line[2:]}</h2>')
        elif line.startswith("- "):
            lines.append(f'<li style="margin:6px 0;">{line[2:]}</li>')
        elif line.strip() == "":
            lines.append("<br>")
        else:
            lines.append(f"<p style='margin:4px 0;'>{line}</p>")
    html_body = "\n".join(lines)
    html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
    return f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, sans-serif; max-width: 700px; margin: auto; padding: 20px; color: #222;">
<h2 style="color:#111;">📰 資訊摘要 — {date_str}</h2>
<p style="color:#888;font-size:13px;">本期共整理 {article_count} 篇文章</p>
<hr style="border:none;border-top:1px solid #ddd;">
{html_body}
<hr style="border:none;border-top:1px solid #ddd;">
<p style="color:#bbb;font-size:11px;">由 info-scraper 自動生成</p>
</body></html>
"""


def synthesize_with_claude(articles: list[dict], preferences_text: str) -> str:
    articles_text = "\n\n".join(
        f"[{a['topic']}] {a['title']}\n{a['content'][:600]}"
        for a in articles
    )
    prompt = f"""你是一位知識合成助理，幫助讀者從最近閱讀的文章中提取複利洞見。

使用者偏好：
{preferences_text}

最近的文章（共 {len(articles)} 篇）：
{articles_text}

請用繁體中文生成一份合成報告，包含以下章節：
## 主要主題
（3-5 個跨文章的反覆出現主題）

## 重要洞見
（5-7 個值得記住的具體洞見，要引用文章標題）

## 可行動項目
（2-4 件讀者現在可以立即行動的事，要具體）

## 值得關注的信號
（1-3 個早期趨勢）

要具體，引用文章標題，不要空泛的觀點。"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=180,
        )
        return result.stdout.strip()
    except Exception as e:
        raise RuntimeError(f"Claude CLI failed: {e}")


def get_since_date(days_back: int) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    return since.strftime("%Y-%m-%d")


def main() -> None:
    settings = Settings.load(CONFIG_PATH, ENV_PATH)
    days_back = settings.config["schedule"]["synthesize_every_days"]
    since_date = get_since_date(days_back)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = settings.output_dir
    preferences_text = (Path(__file__).parent / settings.preferences_path).read_text()

    print(f"[synthesizer] Loading articles since {since_date}...")
    articles = load_recent_articles(output_dir, since_date)

    if not articles:
        print("[synthesizer] No new articles since last synthesis. Skipping.")
        return

    print(f"[synthesizer] Synthesizing {len(articles)} articles with Claude...")
    try:
        report = synthesize_with_claude(articles, preferences_text)
    except RuntimeError as e:
        print(f"[synthesizer] ERROR: {e}", file=sys.stderr)
        send_failure_email("synthesizer", str(e), settings)
        return

    synthesis_dir = output_dir / "synthesis"
    synthesis_dir.mkdir(exist_ok=True)
    report_path = synthesis_dir / f"{today}-synthesis.md"
    report_path.write_text(f"# Synthesis Report -- {today}\n\n{report}", encoding="utf-8")
    print(f"[synthesizer] Report saved to {report_path}")

    if DRY_RUN:
        print("[dry-run] Would send email. Report preview:")
        print(report[:500])
        return

    html = format_synthesis_email(report, len(articles), today)
    try:
        send_email(f"📰 資訊摘要 — {today}", html, settings)
        print(f"[synthesizer] Email sent to {settings.config['email']['to']}")
    except Exception as e:
        error_msg = f"Email send failed: {e}\nReport saved at {report_path}"
        print(f"[synthesizer] ERROR: {error_msg}", file=sys.stderr)
        send_failure_email("synthesizer/email", error_msg, settings)


if __name__ == "__main__":
    main()
