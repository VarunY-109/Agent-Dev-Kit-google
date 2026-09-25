#!/usr/bin/env python3
"""
Commit Scheduler - Reads trajectory and determines today's commit count.
Uses date-based calculation instead of index file.
"""
import os
import subprocess
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMIT_SCHEDULE_FILE = os.path.join(REPO_ROOT, ".commit_schedule")

# Start date: when the automation began
START_DATE = datetime(2026, 9, 20, tzinfo=timezone.utc)


def get_today_commits_from_git():
    """Get number of commits made today by the bot on the current branch."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", "--after=" + today + "T00:00:00Z", "--author=github-actions[bot]", "--oneline"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        return len(lines)
    except Exception:
        return 0


def main():
    # Read trajectory
    with open(COMMIT_SCHEDULE_FILE, "r") as f:
        trajectory = [int(x.strip()) for x in f.read().strip().split(",")]

    # Calculate day number from start date
    today = datetime.now(timezone.utc).date()
    days_since_start = (today - START_DATE.date()).days
    trajectory_index = days_since_start % len(trajectory)

    # Get today's target
    target = trajectory[trajectory_index]

    # How many already done today
    done_today = get_today_commits_from_git()

    # How many more needed
    remaining = max(0, target - done_today)

    # Output the number of commits to make
    print(remaining)


if __name__ == "__main__":
    main()
