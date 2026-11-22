"""Unit tests for the registry site generator. Standard library only.

The generator is factored so local folders and fixture data can drive
every step, discovery included, with no network involved.

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
sys.path.insert(0, ROOT)

import registry_build as rb
import skilldoctor as sd

WHEN = datetime(2026, 11, 22)

CLEAN = """---
name: %s
description: %s
---

# %s

Use this skill when the user wants this done well.
"""

WARN = """---
name: %s
description: %s
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

NOTES_DESC = "Tidies raw meeting notes into a short brief with decisions and owners."
STATUS_DESC = "Drafts a weekly status update from finished tasks and open questions."


def write_skill(root, folder_name, template=CLEAN, description=NOTES_DESC):
    folder = os.path.join(root, folder_name)
    os.makedirs(folder)
    text = template % (folder_name, description, folder_name)
    with open(os.path.join(folder, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return folder


def project(audit_path="skills", slug="fixture--proj", source="listed"):
    return {
        "slug": slug,
        "name": "Fixture",
        "repo": "https://github.com/fixture/proj",
        "audit_path": audit_path,
        "homepage": "https://example.com/",
        "source": source,
    }


def payload(total, fail, health):
    return {
        "summary": {"total": total, "ok": total - fail, "warn": 0, "fail": fail},
        "health_score": health,
    }


class SummarizeTests(unittest.TestCase):
    def test_passing_payload_is_current_with_its_health_score(self):
        result = rb.summarize(payload(15, 0, 98))
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["score"], 98)
        self.assertEqual(result["skills"], 15)

    def test_any_failure_is_a_recheck(self):
        result = rb.summarize(payload(6, 1, 60))
        self.assertEqual(result["status"], "recheck")
        self.assertIsNone(result["score"])
        self.assertEqual(result["failures"], 1)

    def test_no_skills_is_a_recheck(self):
        result = rb.summarize(payload(0, 0, None))
        self.assertEqual(result["status"], "recheck")
        self.assertEqual(result["skills"], 0)


class VerifyLocalTests(unittest.TestCase):
    def test_clean_collection_is_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(os.path.join(tmp, "skills"), "alpha")
            write_skill(os.path.join(tmp, "skills"), "beta", description=STATUS_DESC)
            entry = rb.verify_local(project(), tmp, WHEN)
            self.assertEqual(entry["status"], "current")
            self.assertEqual(entry["score"], 100)
            self.assertEqual(entry["skills"], 2)
            self.assertEqual(entry["verified"], "2026-11-22")
            self.assertEqual(entry["badge"], "badges/fixture--proj.svg")

    def test_failing_collection_is_a_recheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(os.path.join(tmp, "skills"), "alpha")
            broken_root = os.path.join(tmp, "skills")
            folder = os.path.join(broken_root, "broken-skill")
            os.makedirs(folder)
            with open(os.path.join(folder, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write(BROKEN)
            entry = rb.verify_local(project(), tmp, WHEN)
            self.assertEqual(entry["status"], "recheck")
            self.assertIsNone(entry["score"])
            self.assertEqual(entry["failures"], 1)

    def test_whole_tree_audit_scores_every_skill_it_finds(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(os.path.join(tmp, "packs", "good", "skills"), "alpha")
            write_skill(
                os.path.join(tmp, "packs", "warned", "skills"),
                "beta",
                template=WARN,
                description=STATUS_DESC,
            )
            entry = rb.verify_local(project("packs"), tmp, WHEN)
            self.assertEqual(entry["status"], "current")
            self.assertEqual(entry["skills"], 2)
            self.assertLess(entry["score"], 100)

    def test_missing_audit_path_is_a_recheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = rb.verify_local(project("nope"), tmp, WHEN)
            self.assertEqual(entry["status"], "recheck")
            self.assertIn("not found", entry["note"])


class ParseIdentitiesTests(unittest.TestCase):
    def test_reads_owner_and_repo_out_of_badge_and_plaque_urls(self):
        texts = [
            "[![x](https://dongdarealest.github.io/skilldoctor/badges/Alice--tools.svg)](y)",
            '<img src="https://dongdarealest.github.io/skilldoctor/badges/Alice--tools-plaque.svg">',
        ]
        found = rb.parse_identities(texts)
        self.assertEqual(found, {("alice", "tools"): ("Alice", "tools")})

    def test_the_plain_mark_enrolls_nothing(self):
        texts = ["https://dongdarealest.github.io/skilldoctor/badges/audited.svg"]
        self.assertEqual(rb.parse_identities(texts), {})

    def test_repo_names_with_hyphens_and_dots_survive(self):
        texts = [
            "https://dongdarealest.github.io/skilldoctor/badges/Bob--my-cool.tools.svg",
            "https://dongdarealest.github.io/skilldoctor/badges/Bob--my-cool.tools-plaque.svg",
        ]
        found = rb.parse_identities(texts)
        self.assertEqual(found, {("bob", "my-cool.tools"): ("Bob", "my-cool.tools")})


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.listed = project("packs", slug="Dongdarealest--skillport")
        self.discovered = project(
            ".", slug="Alice--tools", source="discovered"
        )

    def test_new_identity_is_enrolled_for_a_root_audit(self):
        kept, dropped = rb.reconcile_projects(
            [self.listed], {("alice", "tools"): ("Alice", "tools")}
        )
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), 2)
        new = kept[1]
        self.assertEqual(new["slug"], "Alice--tools")
        self.assertEqual(new["repo"], "https://github.com/Alice/tools")
        self.assertEqual(new["audit_path"], ".")
        self.assertEqual(new["source"], "discovered")

    def test_discovered_entry_still_wearing_the_badge_is_kept(self):
        kept, dropped = rb.reconcile_projects(
            [self.listed, self.discovered],
            {("alice", "tools"): ("Alice", "tools")},
        )
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), 2)

    def test_discovered_entry_that_took_the_badge_down_is_dropped(self):
        kept, dropped = rb.reconcile_projects([self.listed, self.discovered], {})
        self.assertEqual([p["slug"] for p in kept], ["Dongdarealest--skillport"])
        self.assertEqual(dropped, ["Alice--tools"])

    def test_listed_entries_survive_an_empty_discovery(self):
        kept, dropped = rb.reconcile_projects([self.listed], {})
        self.assertEqual(kept, [self.listed])
        self.assertEqual(dropped, [])

    def test_no_discovery_run_changes_nothing(self):
        kept, dropped = rb.reconcile_projects(
            [self.listed, self.discovered], None
        )
        self.assertEqual(kept, [self.listed, self.discovered])
        self.assertEqual(dropped, [])

    def test_discovery_without_a_token_is_skipped(self):
        self.assertIsNone(rb.discover_identities(None))
        self.assertIsNone(rb.discover_identities("tok", search_fn=lambda: 1 / 0))

    def test_discovery_uses_the_injected_search(self):
        found = rb.discover_identities(
            "tok",
            search_fn=lambda: [
                "see https://dongdarealest.github.io/skilldoctor/badges/Carol--kit.svg here",
            ],
        )
        self.assertEqual(found, {("carol", "kit"): ("Carol", "kit")})


class ImageTests(unittest.TestCase):
    def test_current_images_carry_the_score(self):
        entry = {"status": "current", "score": 98, "skills": 30}
        self.assertIn("98", rb.badge_for(entry, WHEN))
        plaque = rb.plaque_for(entry, WHEN)
        self.assertIn("Health 98 / 100", plaque)
        self.assertIn("30 skills · 0 failures · November 2026", plaque)

    def test_recheck_images_are_grey_and_say_so(self):
        entry = {"status": "recheck", "score": None, "skills": 3}
        self.assertIn("RECHECK", rb.badge_for(entry, WHEN))
        plaque = rb.plaque_for(entry, WHEN)
        self.assertIn("Recheck needed", plaque)
        self.assertIn("#8A8680", plaque)


class WriteSiteTests(unittest.TestCase):
    def entry(self, slug="Alice--tools", status="current", score=90):
        return {
            "slug": slug,
            "name": "Alice/tools",
            "repo": "https://github.com/Alice/tools",
            "homepage": "https://github.com/Alice/tools",
            "verified": "2026-11-22",
            "badge": "badges/%s.svg" % slug,
            "plaque": "badges/%s-plaque.svg" % slug,
            "status": status,
            "score": score,
            "skills": 4,
            "failures": 0,
            "note": None,
        }

    def test_write_site_generates_images_and_removes_stale_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            badges = os.path.join(tmp, "badges")
            os.makedirs(badges)
            with open(os.path.join(badges, "Gone--repo.svg"), "w") as fh:
                fh.write("stale")
            rb.write_site([self.entry()], WHEN, docs_dir=tmp)
            self.assertTrue(os.path.exists(os.path.join(badges, "Alice--tools.svg")))
            self.assertTrue(
                os.path.exists(os.path.join(badges, "Alice--tools-plaque.svg"))
            )
            self.assertFalse(os.path.exists(os.path.join(badges, "Gone--repo.svg")))
            generic = os.path.join(badges, "audited.svg")
            self.assertTrue(os.path.exists(generic))
            with open(generic, encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip(), sd.badge_svg())

    def test_index_carries_the_snippet_generator(self):
        page = rb.render_index([self.entry()], WHEN)
        self.assertIn('id="repo-input"', page)
        self.assertIn('id="repo-go"', page)
        self.assertIn("Alice--tools.svg", page)
        self.assertIn("next daily verification", page)


if __name__ == "__main__":
    unittest.main()
