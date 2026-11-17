"""Tests for scripts/check-rules-sync.py. Run: python3 -m unittest discover -s tests"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_rules_sync", ROOT / "scripts" / "check-rules-sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

LOCK = {"source": "FedRAMP/rules", "version": "2026.11.02.01", "commit": "64fa769510416fa75fd00a4689466094265b8083"}


def sources(sha):
    return {"rules": {"repo": "fedramp/rules", "ref": "main", "sha": sha}}


def never(*_):
    raise AssertionError("compare shouldn't be called when the commits match")


class CheckRulesSync(unittest.TestCase):
    def test_same_commit_passes(self):
        ok, message = sync.check(sources(LOCK["commit"]), LOCK, compare=never)
        self.assertTrue(ok)
        self.assertIn("the approved commit", message)

    def test_docs_ahead_fails(self):
        ok, message = sync.check(sources("a" * 40), LOCK, compare=lambda *_: ("ahead", 3, 0))
        self.assertFalse(ok)
        self.assertIn("docs is ahead by 3 commit(s)", message)

    def test_brain_ahead_fails(self):
        ok, message = sync.check(sources("b" * 40), LOCK, compare=lambda *_: ("behind", 0, 2))
        self.assertFalse(ok)
        self.assertIn("brain is ahead by 2 commit(s)", message)

    def test_diverged_fails(self):
        ok, message = sync.check(sources("c" * 40), LOCK, compare=lambda *_: ("diverged", 1, 1))
        self.assertFalse(ok)
        self.assertIn("diverged", message)

    def test_api_error_still_fails(self):
        def broken(*_):
            raise OSError("no network")
        ok, message = sync.check(sources("d" * 40), LOCK, compare=broken)
        self.assertFalse(ok)
        self.assertIn("Couldn't tell which side is ahead", message)

    def test_repo_files_match_today(self):
        import json
        ok, _ = sync.check(json.loads((ROOT / "upstream" / "_sources.json").read_text()),
                           json.loads((ROOT / "fedramp-rules.lock.json").read_text()), compare=never)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
