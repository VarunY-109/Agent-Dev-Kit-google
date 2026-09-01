#!/usr/bin/env python3
"""
Commit Scheduler - Reads trajectory and determines today's commit count.
"""
import os
import subprocess
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMIT_SCHEDULE_FILE = os.path.join(REPO_ROOT, ".commit_schedule")
TRAJECTORY_INDEX_FILE = os.path.join(REPO_ROOT, ".trajectory_index")


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

    # Read current index
    with open(TRAJECTORY_INDEX_FILE, "r") as f:
        index = int(f.read().strip())

    # Get today's target
    target = trajectory[index % len(trajectory)]

    # How many already done today
    done_today = get_today_commits_from_git()

    # How many more needed
    remaining = max(0, target - done_today)

    # Advance index if this is the first run of the day (0 commits done yet)
    if done_today == 0:
        new_index = (index + 1) % len(trajectory)
        with open(TRAJECTORY_INDEX_FILE, "w") as f:
            f.write(str(new_index))

    # Output the number of commits to make
    print(remaining)


if __name__ == "__main__":
    main()
