#!/usr/bin/env python3
"""
Synthesizer: generates a synthesis report from recent articles and emails it.
Run every 2 days at 09:00 via cron.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import Settings
from email_utils import send_email, send_failure_email

CONFIG_PATH = Path(__file__).parent / "config.yaml"
ENV_PATH = Path(__file__).parent / ".env"
DRY_RUN = "--dry-run" in sys.argv


import manifest as manifest_mod


def load_unsynthesized_articles(output_dir: Path, manifest_path: Path) -> list[dict]:
    """Collect dated articles not yet in manifest (shared walker skips synthesis/archive/no-date)."""
    done = manifest_mod.load(manifest_path)
    articles = []
    for md_file in manifest_mod.iter_dated_articles(output_dir):
        rel = manifest_mod.rel_path(md_file, output_dir)
        if rel in done:
            continue
        text = md_file.read_text(encoding="utf-8")
        title = text.split("\n")[0].lstrip("# ").strip()
        articles.append({
            "title": title,
            "topic": md_file.parent.name,
            "date": md_file.name[:10],
            "content": text[:1500],
            "path": str(md_file),
            "rel": rel,
        })
    return articles


def load_previous_synthesis(synthesis_dir: Path, today: str) -> str:
    """Return the most recent synthesis file before today, or empty string."""
    files = sorted(
        [f for f in synthesis_dir.glob("????-??-??-synthesis.md") if f.name[:10] < today],
        reverse=True,
    )
    if files:
        text = files[0].read_text(encoding="utf-8")
        # Trim to first 3000 chars to keep prompt size reasonable
        return text[:3000]
    return ""


def deduplicate_action_items(report: str) -> str:
    """Remove duplicate ### N. items inside 可行動項目 section."""
    lines = report.split("\n")
    result = []
    in_action_section = False
    seen_nums: set[str] = set()
    skip_block = False

    for line in lines:
        if re.match(r"^## 可行動項目", line):
            in_action_section = True
            seen_nums = set()
            skip_block = False
        elif line.startswith("## ") and in_action_section:
            in_action_section = False
            skip_block = False

        if in_action_section:
            m = re.match(r"^### (\d+)[.\s]", line)
            if m:
                num = m.group(1)
                if num in seen_nums:
                    skip_block = True
                    continue
                seen_nums.add(num)
                skip_block = False

        if not skip_block:
            result.append(line)

    return "\n".join(result)


def format_synthesis_email(report_text: str, article_count: int, date_str: str) -> str:
    # Convert markdown to HTML with proper ul wrapping
    result_lines = []
    in_list = False

    for line in report_text.split("\n"):
        if line.startswith("### "):
            if in_list:
                result_lines.append("</ul>")
                in_list = False
            result_lines.append(
                f'<h4 style="color:#1a56db;font-size:15px;font-weight:600;margin:20px 0 6px;">'
                f'{line[4:]}</h4>'
            )
        elif line.startswith("## "):
            if in_list:
                result_lines.append("</ul>")
                in_list = False
            result_lines.append(
                f'<h3 style="color:#111;font-size:19px;font-weight:700;margin:32px 0 10px;'
                f'padding-left:14px;border-left:4px solid #1a56db;">'
                f'{line[3:]}</h3>'
            )
        elif line.startswith("# "):
            if in_list:
                result_lines.append("</ul>")
                in_list = False
            result_lines.append(
                f'<h2 style="color:#0a0a0a;font-size:23px;font-weight:800;margin:0 0 8px;">'
                f'{line[2:]}</h2>'
            )
        elif line.startswith("- "):
            if not in_list:
                result_lines.append('<ul style="margin:8px 0 14px;padding-left:22px;">')
                in_list = True
            result_lines.append(
                f'<li style="margin:7px 0;line-height:1.65;">{line[2:]}</li>'
            )
        elif line.strip() == "":
            if in_list:
                result_lines.append("</ul>")
                in_list = False
            result_lines.append("")
        else:
            if in_list:
                result_lines.append("</ul>")
                in_list = False
            result_lines.append(
                f'<p style="margin:7px 0;line-height:1.7;font-size:16px;">{line}</p>'
            )

    if in_list:
        result_lines.append("</ul>")

    html_body = "\n".join(result_lines)
    html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.7; background: #f0f2f5; margin: 0; padding: 24px;">
<div style="max-width: 680px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 3px 12px rgba(0,0,0,0.10);">

  <!-- Header -->
  <div style="background: linear-gradient(135deg, #1a56db 0%, #0e3fa8 100%); padding: 30px 36px;">
    <h1 style="color: #fff; margin: 0 0 6px; font-size: 24px; font-weight: 700; letter-spacing: -0.3px;">📰 資訊摘要</h1>
    <p style="color: rgba(255,255,255,0.75); margin: 0; font-size: 14px;">{date_str}&nbsp;&nbsp;·&nbsp;&nbsp;共整理 {article_count} 篇文章</p>
  </div>

  <!-- Body -->
  <div style="padding: 30px 36px; color: #1a1a1a;">
{html_body}
  </div>

  <!-- Footer -->
  <div style="padding: 14px 36px; background: #f7f8fa; border-top: 1px solid #e8eaed; text-align: center;">
    <p style="color: #aaa; font-size: 12px; margin: 0;">由 info-scraper 自動生成</p>
  </div>

</div>
</body></html>
"""


CHUNK_SIZE = 25

REQUIRED_SECTIONS = ("## 主要主題", "## 重要洞見", "## 可行動項目", "## 值得關注的信號")


def _validate_report(report: str) -> bool:
    """Final synthesis must contain all four required section headers."""
    return all(section in report for section in REQUIRED_SECTIONS)


def _run_claude(prompt: str, timeout: int = 300) -> str:
    """Run claude -p with the given prompt, with one retry on failure."""
    for attempt in range(2):
        try:
            result = subprocess.run(
                ["claude", "-p"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout.strip()
            if not output:
                raise RuntimeError("Empty output from Claude CLI")
            return output
        except Exception as e:
            if attempt == 0:
                print(f"[synthesizer] Attempt 1 failed ({e}), retrying...", file=sys.stderr)
            else:
                raise RuntimeError(f"Claude CLI failed: {e}")


def _summarize_chunk(chunk: list[dict]) -> str:
    """Summarize one chunk of articles into a compact JSON string."""
    articles_text = "\n\n".join(
        f"[{a['topic']}] {a['title']}\n{a['content'][:800]}"
        for a in chunk
    )
    prompt = f"""你是一位知識合成助理。以下是 {len(chunk)} 篇文章，請提取每篇的核心主張和關鍵洞見，以及 2-3 個跨文章的共同主題。

以 JSON 格式回應，不要有任何其他文字：
{{"articles":[{{"title":"...","topic":"...","core_claim":"一句話核心主張","key_insight":"一句話最重要洞見"}}],"themes":["跨文章主題1","跨文章主題2"]}}

文章：
{articles_text}"""
    return _run_claude(prompt)


def synthesize_with_claude(articles: list[dict], preferences_text: str, previous_synthesis: str) -> str:
    # Split into chunks and summarize each independently to stay within claude -p limits
    chunks = [articles[i:i + CHUNK_SIZE] for i in range(0, len(articles), CHUNK_SIZE)]
    print(f"[synthesizer] Processing {len(chunks)} chunk(s) of up to {CHUNK_SIZE} articles each...")

    summaries: list[str] = []
    for idx, chunk in enumerate(chunks, 1):
        print(f"[synthesizer] Summarizing chunk {idx}/{len(chunks)} ({len(chunk)} articles)...")
        # Invariant: a chunk failure must fail the whole run so main() does NOT
        # mark these articles synthesized — they get retried next run (manifest-based).
        # Silently skipping would mark unsynthesized articles as done → archived without synthesis.
        summaries.append(_summarize_chunk(chunk))

    if not summaries:
        raise RuntimeError("No summaries to synthesize from")

    combined = "\n\n".join(summaries)
    prev_section = (
        f"\n上一期合成報告（已建立的觀點，本期請勿重複，只報告新增的角度）：\n{previous_synthesis}\n"
        if previous_synthesis
        else ""
    )
    base_prompt = f"""你是一位知識合成助理，幫助讀者從最近閱讀的文章中提取複利洞見。

使用者偏好：
{preferences_text}
{prev_section}
以下是 {len(articles)} 篇文章的結構化摘要（分批彙整）：
{combined}

請用繁體中文生成一份合成報告，包含以下章節：
## 主要主題
（3-5 個跨文章的反覆出現主題，只寫上一期沒有涵蓋的新主題或新角度，每個主題要深度展開而非列點）

## 重要洞見
（5-7 個值得記住的具體洞見，要引用文章標題）

## 可行動項目
（2-4 件讀者現在可以立即行動的事，要具體）
重要：每個項目只寫一次，不要用不同標題重複同一件事。每個 ### 編號只出現一次。

## 值得關注的信號
（1-3 個早期趨勢）

要具體，引用文章標題，不要空泛的觀點。

==== 輸出格式硬性要求 ====
1. 直接輸出報告本身，第一行必須是 `## 主要主題`。
2. 禁止任何前言、開場白、結尾說明、meta 評論（例如「報告完成」、「幾個說明」、「我來分析」、「以下是報告」之類）。
3. 報告必須包含全部四個章節：## 主要主題、## 重要洞見、## 可行動項目、## 值得關注的信號。任何章節缺失就算失敗。"""

    report = _run_claude(base_prompt)
    if _validate_report(report):
        return report

    print("[synthesizer] WARNING: report missing required sections, retrying with stricter prompt...", file=sys.stderr)
    retry_prompt = base_prompt + (
        "\n\n你上一次的輸出缺少必要章節或只回了 meta 評論。"
        "這次請務必輸出完整報告主體，從 `## 主要主題` 開始，"
        "四個章節（主要主題 / 重要洞見 / 可行動項目 / 值得關注的信號）一個都不能少。"
    )
    report = _run_claude(retry_prompt)
    if not _validate_report(report):
        missing = [s for s in REQUIRED_SECTIONS if s not in report]
        raise RuntimeError(f"Report validation failed after retry. Missing sections: {missing}")
    return report


def main() -> None:
    settings = Settings.load(CONFIG_PATH, ENV_PATH)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = settings.output_dir
    preferences_text = (Path(__file__).parent / settings.preferences_path).read_text()

    synthesis_dir = output_dir / "synthesis"
    synthesis_dir.mkdir(exist_ok=True)

    manifest_path = manifest_mod.default_path(output_dir)
    print(f"[synthesizer] Loading unsynthesized articles (manifest-based)...")
    articles = load_unsynthesized_articles(output_dir, manifest_path)

    if not articles:
        print("[synthesizer] No unsynthesized articles. Skipping.")
        return

    previous_synthesis = load_previous_synthesis(synthesis_dir, today)
    if previous_synthesis:
        print(f"[synthesizer] Loaded previous synthesis for dedup context.")

    print(f"[synthesizer] Synthesizing {len(articles)} articles with Claude...")
    try:
        report = synthesize_with_claude(articles, preferences_text, previous_synthesis)
    except RuntimeError as e:
        print(f"[synthesizer] ERROR: {e}", file=sys.stderr)
        send_failure_email("synthesizer", str(e), settings)
        return

    report = deduplicate_action_items(report)

    if DRY_RUN:
        # True dry-run: no disk write, no email, no manifest mutation.
        print(f"[dry-run] Would save {today}-synthesis.md, send email, mark {len(articles)} articles.")
        print("[dry-run] Report preview:")
        print(report[:500])
        return

    report_path = synthesis_dir / f"{today}-synthesis.md"
    report_path.write_text(f"# Synthesis Report -- {today}\n\n{report}", encoding="utf-8")
    print(f"[synthesizer] Report saved to {report_path}")

    html = format_synthesis_email(report, len(articles), today)
    try:
        send_email(f"📰 資訊摘要 — {today}", html, settings)
        print(f"[synthesizer] Email sent to {settings.config['email']['to']}")
    except Exception as e:
        error_msg = f"Email send failed: {e}\nReport saved at {report_path}"
        print(f"[synthesizer] ERROR: {error_msg}", file=sys.stderr)
        send_failure_email("synthesizer/email", error_msg, settings)
        return

    # Mark these articles synthesized only after successful report + email.
    manifest_mod.append(manifest_path, [a["rel"] for a in articles])
    print(f"[synthesizer] Marked {len(articles)} articles as synthesized.")


if __name__ == "__main__":
    main()
