"""Unit tests for the registry site generator. Standard library only.

The generator is factored so a local folder can be verified without
cloning, and these tests use fixture folders on disk throughout.

Run from the project root:
    python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import registry_build as rb

WHEN = datetime(2026, 11, 22)

CLEAN = """---
name: %s
description: Tidies raw meeting notes into a short brief with decisions, owners, and dates.
---

# %s

Use this skill when the user pastes rough notes and wants a tidy brief.
"""

WARN = """---
name: %s
description: Tidies raw meeting notes into a short brief with decisions, owners, and dates.
---

# %s

Before starting, ask the user for the API key the export step needs.
"""

BROKEN = """---
name: some-other-name
description: Formats a changelog from merged pull requests for a release notes page.
---

# Broken

The name above does not match this folder, so the audit fails it.
"""


OTHER_CLEAN = CLEAN.replace(
    "Tidies raw meeting notes into a short brief with decisions, owners, and dates.",
    "Drafts a weekly status update from finished tasks and open questions.",
)


def write_skill(root, folder_name, text):
    folder = os.path.join(root, folder_name)
    os.makedirs(folder)
    with open(os.path.join(folder, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(text % (folder_name, folder_name) if "%s" in text else text)
    return folder


def project(audit_path="skills"):
    return {
        "slug": "fixture",
        "name": "Fixture",
        "repo": "https://example.com/fixture",
        "audit_path": audit_path,
        "homepage": "https://example.com/",
    }


def payload(total, fail, health):
    return {
        "summary": {
            "total": total,
            "ok": total - fail,
            "warn": 0,
            "fail": fail,
        },
        "health_score": health,
    }


class FindUnitsTests(unittest.TestCase):
    def test_pack_shape_audits_each_pack_skills_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pack in ("pack-one", "pack-two"):
                write_skill(os.path.join(tmp, pack, "skills"), "alpha", CLEAN)
            units = rb.find_units(tmp)
            self.assertEqual(
                units,
                [
                    os.path.join(tmp, "pack-one", "skills"),
                    os.path.join(tmp, "pack-two", "skills"),
                ],
            )

    def test_flat_shape_audits_each_skill_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(tmp, "alpha", CLEAN)
            write_skill(tmp, "beta", CLEAN)
            units = rb.find_units(tmp)
            self.assertEqual(
                units,
                [os.path.join(tmp, "alpha"), os.path.join(tmp, "beta")],
            )

    def test_single_skill_folder_is_one_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(tmp, "alpha", CLEAN)
            skill_folder = os.path.join(tmp, "alpha")
            self.assertEqual(rb.find_units(skill_folder), [skill_folder])

    def test_empty_folder_has_no_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rb.find_units(tmp), [])


class SummarizeTests(unittest.TestCase):
    def test_all_passing_is_current_with_the_lowest_score(self):
        result = rb.summarize([payload(3, 0, 100), payload(3, 0, 92)])
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["score"], 92)
        self.assertEqual(result["skills"], 6)
        self.assertEqual(result["failures"], 0)

    def test_any_failure_is_a_recheck(self):
        result = rb.summarize([payload(3, 0, 100), payload(2, 1, 60)])
        self.assertEqual(result["status"], "recheck")
        self.assertIsNone(result["score"])
        self.assertEqual(result["failures"], 1)

    def test_no_skills_is_a_recheck(self):
        result = rb.summarize([payload(0, 0, None)])
        self.assertEqual(result["status"], "recheck")
        self.assertEqual(result["skills"], 0)


class VerifyLocalTests(unittest.TestCase):
    def test_clean_collection_is_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(os.path.join(tmp, "skills"), "alpha", CLEAN)
            write_skill(os.path.join(tmp, "skills"), "beta", OTHER_CLEAN)
            entry = rb.verify_local(project(), tmp, WHEN)
            self.assertEqual(entry["status"], "current")
            self.assertEqual(entry["score"], 100)
            self.assertEqual(entry["skills"], 2)
            self.assertEqual(entry["verified"], "2026-11-22")

    def test_failing_collection_is_a_recheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(os.path.join(tmp, "skills"), "alpha", CLEAN)
            write_skill(os.path.join(tmp, "skills"), "broken-skill", BROKEN)
            entry = rb.verify_local(project(), tmp, WHEN)
            self.assertEqual(entry["status"], "recheck")
            self.assertIsNone(entry["score"])
            self.assertEqual(entry["failures"], 1)

    def test_pack_shape_scores_the_weakest_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(os.path.join(tmp, "packs", "good", "skills"), "alpha", CLEAN)
            write_skill(os.path.join(tmp, "packs", "warned", "skills"), "beta", WARN)
            entry = rb.verify_local(project("packs"), tmp, WHEN)
            self.assertEqual(entry["status"], "current")
            self.assertEqual(entry["skills"], 2)
            self.assertLess(entry["score"], 100)

    def test_missing_audit_path_is_a_recheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = rb.verify_local(project("nope"), tmp, WHEN)
            self.assertEqual(entry["status"], "recheck")
            self.assertIn("not found", entry["note"])


class ImageTests(unittest.TestCase):
    def test_current_images_carry_the_score(self):
        entry = {"status": "current", "score": 92, "skills": 15}
        self.assertIn("92", rb.badge_for(entry, WHEN))
        plaque = rb.plaque_for(entry, WHEN)
        self.assertIn("Health 92 / 100", plaque)
        self.assertIn("15 skills · 0 failures · November 2026", plaque)

    def test_recheck_images_are_grey_and_say_so(self):
        entry = {"status": "recheck", "score": None, "skills": 3}
        self.assertIn("RECHECK", rb.badge_for(entry, WHEN))
        plaque = rb.plaque_for(entry, WHEN)
        self.assertIn("Recheck needed", plaque)
        self.assertIn("#8A8680", plaque)


if __name__ == "__main__":
    unittest.main()
