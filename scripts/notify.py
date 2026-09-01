#!/usr/bin/env python3
"""
Telegram Notification Agent - Sends status updates via Telegram.
Usage: python notify.py <status> <commits_today>
  status: success, failure, rest
"""
import os
import sys
import subprocess
import requests
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAJECTORY_INDEX_FILE = os.path.join(REPO_ROOT, ".trajectory_index")
COMMIT_SCHEDULE_FILE = os.path.join(REPO_ROOT, ".commit_schedule")


def get_current_day():
    """Get current day number from trajectory index."""
    try:
        with open(TRAJECTORY_INDEX_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def get_today_target():
    """Get today's target commit count."""
    try:
        with open(COMMIT_SCHEDULE_FILE, "r") as f:
            trajectory = [int(x.strip()) for x in f.read().strip().split(",")]
        with open(TRAJECTORY_INDEX_FILE, "r") as f:
            index = int(f.read().strip())
        return trajectory[(index - 1) % len(trajectory)]
    except Exception:
        return 0


def get_recent_commits():
    """Get list of commits made today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", "--after=" + today + "T00:00:00Z", "--author=github-actions[bot]", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        files = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        return files
    except Exception:
        return []


def send_telegram(message):
    """Send message via Telegram bot."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not set", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False


def main():
    status = sys.argv[1] if len(sys.argv) > 1 else "success"
    commits_today = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    day = get_current_day()
    target = get_today_target()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if status == "success":
        files = get_recent_commits()
        file_list = "\n".join([f"  - {f}" for f in files]) if files else "  (no files)"
        message = (
            f"✅ <b>Commit Tracker - Day {day}</b>\n\n"
            f"Status: <b>SUCCESS</b>\n"
            f"Time: {now}\n"
            f"Commits today: {commits_today}/{target}\n"
            f"Files committed:\n{file_list}\n"
            f"Branch: main"
        )
    elif status == "failure":
        message = (
            f"❌ <b>Commit Tracker - Day {day}</b>\n\n"
            f"Status: <b>FAILED</b>\n"
            f"Time: {now}\n"
            f"Error occurred during workflow execution.\n"
            f"Check Actions tab for details."
        )
    elif status == "rest":
        message = (
            f"💤 <b>Commit Tracker - Day {day}</b>\n\n"
            f"Status: <b>REST DAY</b>\n"
            f"Time: {now}\n"
            f"No commits scheduled today.\n"
            f"Next active day: tomorrow"
        )
    else:
        message = f"ℹ️ Commit Tracker - Day {day}: Unknown status '{status}'"

    send_telegram(message)
    print(f"Notification sent: {status}")


if __name__ == "__main__":
    main()
