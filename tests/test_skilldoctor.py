"""Unit tests for SkillDoctor. Standard library only.

Run from the project root:
    python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import skilldoctor as sd

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(os.path.dirname(HERE), "examples")


def write_skill(root, folder_name, text):
    folder = os.path.join(root, folder_name)
    os.makedirs(folder)
    with open(os.path.join(folder, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return folder


class FrontmatterTests(unittest.TestCase):
    def test_parses_simple_fields(self):
        fields, body, error = sd.parse_frontmatter(
            "---\nname: demo\ndescription: A demo skill.\n---\n\nBody text.\n"
        )
        self.assertIsNone(error)
        self.assertEqual(fields["name"], "demo")
        self.assertEqual(fields["description"], "A demo skill.")
        self.assertIn("Body text.", body)

    def test_quoted_values_are_unwrapped(self):
        fields, _, error = sd.parse_frontmatter(
            '---\nname: demo\ndescription: "Quoted: with colon"\n---\nBody.\n'
        )
        self.assertIsNone(error)
        self.assertEqual(fields["description"], "Quoted: with colon")

    def test_missing_block_is_an_error(self):
        _, _, error = sd.parse_frontmatter("# Just a heading\n")
        self.assertIsNotNone(error)

    def test_unclosed_block_is_an_error(self):
        _, _, error = sd.parse_frontmatter("---\nname: demo\n")
        self.assertIsNotNone(error)

    def test_line_without_colon_is_an_error(self):
        _, _, error = sd.parse_frontmatter("---\nname demo\n---\nBody.\n")
        self.assertIsNotNone(error)


class TokenTests(unittest.TestCase):
    def test_estimate_is_chars_over_four(self):
        self.assertEqual(sd.estimate_tokens("a" * 40), 10)
        self.assertEqual(sd.estimate_tokens("a" * 41), 11)
        self.assertEqual(sd.estimate_tokens(""), 0)


class AuditTests(unittest.TestCase):
    def test_clean_example_is_ok(self):
        report = sd.audit_skill(os.path.join(EXAMPLES, "clean-skill"), "examples")
        self.assertEqual(report.verdict, "OK")
        self.assertEqual(report.name, "clean-skill")
        self.assertGreater(report.tokens, 0)

    def test_invalid_example_fails(self):
        report = sd.audit_skill(os.path.join(EXAMPLES, "invalid-skill"), "examples")
        self.assertEqual(report.verdict, "FAIL")
        messages = " ".join(f.message for f in report.findings)
        self.assertIn("missing required field: description", messages)
        self.assertIn("not kebab-case", messages)
        self.assertIn("does not match its folder", messages)

    def test_risky_example_fails_with_security_findings(self):
        report = sd.audit_skill(os.path.join(EXAMPLES, "risky-skill"), "examples")
        self.assertEqual(report.verdict, "FAIL")
        security = [f for f in report.findings if f.kind == "security"]
        self.assertTrue(any(f.severity == "high" for f in security))
        labels = " ".join(f.message for f in security)
        self.assertIn("pipes a network download", labels)
        self.assertIn("ignore its previous instructions", labels)
        self.assertIn("credential", labels)
        self.assertIn("base64", labels)

    def test_valid_skill_in_temp_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = write_skill(
                tmp, "note-taker",
                "---\nname: note-taker\ndescription: Takes tidy notes.\n---\n\nBe tidy.\n",
            )
            report = sd.audit_skill(folder, "test")
            self.assertEqual(report.verdict, "OK")

    def test_missing_file_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = sd.audit_skill(os.path.join(tmp, "ghost"), "test")
            self.assertEqual(report.verdict, "FAIL")


def write_muse_skill(root, folder_name, yaml_text, body="# A Muse skill\n\nBe helpful.\n"):
    folder = write_skill(root, folder_name, body)
    with open(os.path.join(folder, "skill.yaml"), "w", encoding="utf-8") as fh:
        fh.write(yaml_text)
    return folder


class MuseFormatTests(unittest.TestCase):
    def test_muse_skill_audits_without_frontmatter_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = write_muse_skill(
                tmp, "morning_brief",
                'name: morning_brief\ntitle: "Morning Brief"\ndescription: "Prepares a short morning briefing."\ncategory: "Work and knowledge"\ninclude_in_prompt: false\n',
            )
            report = sd.audit_skill(folder, "test")
            self.assertEqual(report.verdict, "OK")
            self.assertEqual(report.name, "morning_brief")
            self.assertEqual(report.description, "Prepares a short morning briefing.")
            messages = " ".join(f.message for f in report.findings)
            self.assertNotIn("missing YAML frontmatter", messages)

    def test_muse_skill_name_must_match_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = write_muse_skill(
                tmp, "morning_brief",
                "name: other_skill\ndescription: A skill whose name points elsewhere.\n",
            )
            report = sd.audit_skill(folder, "test")
            self.assertEqual(report.verdict, "FAIL")
            messages = " ".join(f.message for f in report.findings)
            self.assertIn("does not match its folder", messages)

    def test_muse_skill_name_must_be_snake_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = write_muse_skill(
                tmp, "note-taker",
                "name: note-taker\ndescription: Takes tidy notes.\n",
            )
            report = sd.audit_skill(folder, "test")
            self.assertEqual(report.verdict, "FAIL")
            messages = " ".join(f.message for f in report.findings)
            self.assertIn("name is not snake_case: note-taker", messages)


class ConflictTests(unittest.TestCase):
    def test_duplicate_names_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "---\nname: shared\ndescription: Does a shared thing.\n---\n\nBody.\n"
            write_skill(os.path.join(tmp, "host-a"), "shared", body)
            write_skill(os.path.join(tmp, "host-b"), "shared", body)
            reports = sd.scan([os.path.join(tmp, "host-a"), os.path.join(tmp, "host-b")])
            self.assertEqual(len(reports), 2)
            for r in reports:
                self.assertEqual(r.verdict, "WARN")
                self.assertTrue(any(f.kind == "conflict" for f in r.findings))

    def test_near_duplicate_descriptions_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            desc = "Formats meeting notes into a summary with decisions and action items listed"
            write_skill(tmp, "alpha", "---\nname: alpha\ndescription: %s.\n---\n\nA.\n" % desc)
            write_skill(tmp, "beta", "---\nname: beta\ndescription: %s.\n---\n\nB.\n" % desc)
            reports = sd.scan([tmp])
            for r in reports:
                self.assertTrue(any("near duplicate" in f.message for f in r.findings))

    def test_distinct_skills_have_no_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(tmp, "alpha", "---\nname: alpha\ndescription: Sorts photos by date taken.\n---\n\nA.\n")
            write_skill(tmp, "beta", "---\nname: beta\ndescription: Drafts polite emails to clients.\n---\n\nB.\n")
            reports = sd.scan([tmp])
            for r in reports:
                self.assertEqual(r.verdict, "OK")


class ScanAndCliTests(unittest.TestCase):
    def test_scan_finds_all_examples(self):
        reports = sd.scan([EXAMPLES])
        names = sorted(r.name for r in reports if r.name)
        self.assertEqual(names, ["Invalid_Skill Name", "clean-skill", "risky-skill"])
        verdicts = {r.name: r.verdict for r in reports if r.name}
        self.assertEqual(verdicts["clean-skill"], "OK")
        self.assertEqual(verdicts["risky-skill"], "FAIL")

    def test_demo_exit_code_is_one_because_examples_include_failures(self):
        self.assertEqual(sd.main(["--demo"]), 1)

    def test_clean_scan_exit_code_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(tmp, "tidy", "---\nname: tidy\ndescription: Keeps things tidy.\n---\n\nTidy.\n")
            self.assertEqual(sd.main([tmp]), 0)

    def test_json_mode_runs(self):
        self.assertEqual(sd.main(["--demo", "--json"]), 1)


if __name__ == "__main__":
    unittest.main()


class QuarantineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = self.tmp
        self.root = os.path.join(self.tmp, "skills")
        bad = os.path.join(self.root, "bad-skill")
        os.makedirs(bad)
        with open(os.path.join(bad, "SKILL.md"), "w") as fh:
            fh.write("---\nname: Wrong_Name\n---\n\nNo description here.\n")
        good = os.path.join(self.root, "good-skill")
        os.makedirs(good)
        with open(os.path.join(good, "SKILL.md"), "w") as fh:
            fh.write("---\nname: good-skill\ndescription: A tidy little skill that formats notes.\n---\n\nBe helpful.\n")

    def tearDown(self):
        if self.old_home is not None:
            os.environ["HOME"] = self.old_home

    def test_quarantine_moves_only_failures_and_restore_undoes(self):
        reports = sd.scan([self.root])
        batch = sd.quarantine_failed(reports, assume_yes=True)
        self.assertIsNotNone(batch)
        self.assertFalse(os.path.exists(os.path.join(self.root, "bad-skill")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "good-skill")))
        self.assertTrue(os.path.exists(os.path.join(batch, "manifest.json")))
        sd.restore_last()
        self.assertTrue(os.path.exists(os.path.join(self.root, "bad-skill")))

    def test_quarantine_declined_moves_nothing(self):
        reports = sd.scan([self.root])
        result = sd.quarantine_failed(reports, assume_yes=False, input_fn=lambda prompt: "n")
        self.assertIsNone(result)
        self.assertTrue(os.path.exists(os.path.join(self.root, "bad-skill")))


class ScoreTest(unittest.TestCase):
    def test_clean_skill_scores_100_a(self):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")
        reports = sd.scan([root])
        clean = [r for r in reports if r.name == "clean-skill"][0]
        self.assertEqual(clean.score, 100)
        self.assertEqual(clean.grade, "A")

    def test_errors_cost_points_and_carry_fixes(self):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")
        reports = sd.scan([root])
        risky = [r for r in reports if r.name == "risky-skill"][0]
        self.assertLess(risky.score, 40)
        fixes = [f.to_dict().get("fix") for f in risky.findings]
        self.assertTrue(any(fixes))


class GuidanceTest(unittest.TestCase):
    def test_failing_report_ends_with_next_step(self):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")
        text = sd.render_text(sd.scan([root]), [root])
        self.assertIn("Next step: skilldoctor --quarantine-failed", text)
        self.assertIn("Health score:", text)

    def test_empty_report_guides_instead_of_dead_ending(self):
        text = sd.render_text([], ["/nonexistent"])
        self.assertIn("skilldoctor --demo", text)


class NestedDiscoveryTest(unittest.TestCase):
    def test_skills_nested_under_a_skills_folder_are_found(self):
        tmp = tempfile.mkdtemp()
        deep = os.path.join(tmp, "collection", "skills", "deep-skill")
        os.makedirs(deep)
        with open(os.path.join(deep, "SKILL.md"), "w") as fh:
            fh.write("---\nname: deep-skill\ndescription: A skill nested two levels down in a collection.\n---\n\nBe helpful.\n")
        reports = sd.scan([os.path.join(tmp, "collection")])
        self.assertEqual([r.name for r in reports], ["deep-skill"])
