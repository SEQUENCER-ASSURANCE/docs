#!/usr/bin/env python3
"""Fail when the FedRAMP rules commit docs mirrors isn't the approved one.

Compares upstream/_sources.json rules.sha (what Nightly sync mirrored) with the commit in
fedramp-rules.lock.json (brain's approved release). When they differ, asks GitHub which side
is ahead on FedRAMP/rules. Reads only. Uses GH_TOKEN or GITHUB_TOKEN if set.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "upstream" / "_sources.json"
LOCK = ROOT / "fedramp-rules.lock.json"


def github_compare(repo, base, head):
    """GitHub's compare status of head against base: ahead, behind, diverged or identical."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/compare/{base}...{head}",
                                     headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read())
    return data["status"], data.get("ahead_by", 0), data.get("behind_by", 0)


def check(sources, lock, compare=github_compare):
    """Return (ok, message)."""
    mirrored, approved = sources["rules"]["sha"], lock["commit"]
    if mirrored == approved:
        return True, (f"docs mirrors FedRAMP/rules {mirrored[:8]}, the approved commit "
                      f"(release {lock['version']}).")
    head = f"docs mirrors FedRAMP/rules {mirrored[:8]}, but brain approves {approved[:8]} (release {lock['version']})."
    try:
        status, ahead, behind = compare(lock["source"], approved, mirrored)
    except Exception as err:  # network or API trouble: still fail, just less specific
        return False, f"{head}\nCouldn't tell which side is ahead: {err}"
    if status == "ahead":
        side = (f"docs is ahead by {ahead} commit(s): FedRAMP changed its rules after the approved "
                "release. Wait for the next release and brain's bump PR, or review the change.")
    elif status == "behind":
        side = (f"brain is ahead by {behind} commit(s): Nightly sync hasn't mirrored the approved "
                "release yet. Rerun Nightly sync.")
    elif status == "diverged":
        side = f"they've diverged ({ahead} ahead, {behind} behind), likely a rewritten FedRAMP history."
    else:
        side = f"GitHub says {status}."
    return False, f"{head}\n{side}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sources", default=str(SOURCES))
    parser.add_argument("--lock", default=str(LOCK))
    args = parser.parse_args(argv)
    ok, message = check(json.loads(Path(args.sources).read_text()), json.loads(Path(args.lock).read_text()))
    print(message, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
