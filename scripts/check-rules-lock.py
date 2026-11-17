#!/usr/bin/env python3
"""Fail when this repo's fedramp-rules.lock.json differs from brain's approved lock.

Copied into each repo as scripts/check-rules-lock.py by brain's update_rules.py. Change it there.

CI runs it with GH_TOKEN set to a sequencer-bot token that can read brain. To test without
the API, pass brain's lock as a file: --brain-lock path/to/fedramp-rules.lock.json
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_NAME = "fedramp-rules.lock.json"
BRAIN_LOCK_URL = f"https://api.github.com/repos/SEQUENCER-ASSURANCE/brain/contents/{LOCK_NAME}?ref=main"


def brain_lock_from_api(token):
    request = urllib.request.Request(BRAIN_LOCK_URL, headers={
        "Accept": "application/vnd.github.raw+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def describe(lock):
    return f'{lock.get("version", "?")} at commit {lock.get("commit", "?")}'


def compare(ours, brains):
    """Return (ok, message)."""
    if ours is None:
        return False, f"This repo has no {LOCK_NAME}. Brain approves {describe(brains)}."
    if ours == brains:
        return True, f"{LOCK_NAME} matches brain: {describe(ours)}."
    keys = sorted(key for key in set(ours) | set(brains) if ours.get(key) != brains.get(key))
    return False, (
        f"{LOCK_NAME} differs from brain's.\n"
        f"  This repo: {describe(ours)}\n"
        f"  Brain:     {describe(brains)}\n"
        f"  Fields that differ: {', '.join(keys)}\n"
        "Merge this repo's rules/<version> follow PR from brain's rollout, or rerun the rollout."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=str(ROOT / LOCK_NAME), help="this repo's lock file")
    parser.add_argument("--brain-lock", help="read brain's lock from this file instead of the API")
    args = parser.parse_args(argv)

    if args.brain_lock:
        brains = json.loads(Path(args.brain_lock).read_text())
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            print("GH_TOKEN isn't set, so brain's lock can't be read.", file=sys.stderr)
            return 2
        brains = brain_lock_from_api(token)

    path = Path(args.lock)
    ours = json.loads(path.read_text()) if path.exists() else None
    ok, message = compare(ours, brains)
    print(message, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
