#!/usr/bin/env python3
"""Build the live SkillDoctor registry site.

Reads registry/projects.json, re-audits every listed public repo from a
fresh shallow clone, and regenerates the GitHub Pages site under docs/:

  docs/registry.json              the machine readable registry state
  docs/index.html                 the public registry page
  docs/badges/<slug>.svg          the small live badge for one project
  docs/badges/<slug>-plaque.svg   the large live plaque for one project

A project whose latest audit passes wears its current score on both
images. A project whose latest audit fails, or that cannot be cloned
or audited, flips to the grey recheck design until it passes again.
The wearer pastes one snippet once; the images are served from the
Pages site and update themselves on every run of this script.

Run by hand with

    python3 tools/registry_build.py

or daily by .github/workflows/registry-verify.yml. The audit step is
factored so a local folder can be verified without cloning, which is
what the tests use. Standard library only, like the tool it serves.
"""

import html
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import skilldoctor as sd

PROJECTS_FILE = os.path.join(ROOT, "registry", "projects.json")
DOCS_DIR = os.path.join(ROOT, "docs")
SITE_URL = "https://dongdarealest.github.io/skilldoctor"

INK = "#141414"
EDGE = "#2E2E2E"
DIVIDER = "#3A3A3A"
GOLD = "#C9A35F"
BONE = "#F2EFE9"
MUTED = "#8A8680"
FONT = sd.BADGE_FONT


# ---------------------------------------------------------------------------
# Finding what to audit. A listed repo is audited in units: collections
# group their skills (one pack folder per group, usually with a skills/
# folder inside; or one folder per skill), and each group is audited on
# its own. The project score is the lowest unit score, the convention
# the registry has used since its first entries: a collection is only
# as strong as its weakest group.
# ---------------------------------------------------------------------------


def contains_skill(folder):
    """True when a SKILL.md sits in this folder or anywhere under it."""
    for _root, _dirs, names in os.walk(folder):
        if "SKILL.md" in names:
            return True
    return False


def find_units(audit_root):
    """Split an audit path into the folders to audit, one per group."""
    if not os.path.isdir(audit_root):
        return []
    units = []
    for name in sorted(os.listdir(audit_root)):
        child = os.path.join(audit_root, name)
        if not os.path.isdir(child):
            continue
        skills_dir = os.path.join(child, "skills")
        if os.path.isdir(skills_dir) and contains_skill(skills_dir):
            units.append(skills_dir)
        elif contains_skill(child):
            units.append(child)
    if not units and contains_skill(audit_root):
        units.append(audit_root)
    return units


def audit_unit(unit_path):
    """Audit one folder and return the machine readable payload."""
    reports = sd.scan([unit_path])
    return sd.build_payload(reports, [unit_path])


def audit_local(audit_root):
    """Audit every unit under a local folder. No network involved."""
    return [audit_unit(unit) for unit in find_units(audit_root)]


def summarize(units):
    """Fold unit payloads into one project status.

    Current means every audited skill passes. Anything else, a failing
    skill, an empty audit path, no skills at all, is a recheck.
    """
    scored = [u for u in units if u["summary"]["total"] > 0]
    skills = sum(u["summary"]["total"] for u in scored)
    failures = sum(u["summary"]["fail"] for u in scored)
    if not scored or skills == 0:
        return {
            "status": "recheck",
            "score": None,
            "skills": 0,
            "failures": failures,
            "note": "No skills found at the audit path.",
        }
    if failures > 0:
        return {
            "status": "recheck",
            "score": None,
            "skills": skills,
            "failures": failures,
            "note": "%d skill(s) currently fail the audit." % failures,
        }
    return {
        "status": "current",
        "score": min(u["health_score"] for u in scored),
        "skills": skills,
        "failures": 0,
        "note": None,
    }


# ---------------------------------------------------------------------------
# Verification. fetch_repo is the only step that touches the network;
# verify_local works on any folder already on disk.
# ---------------------------------------------------------------------------


def base_entry(project, when):
    return {
        "slug": project["slug"],
        "name": project["name"],
        "repo": project["repo"],
        "homepage": project["homepage"],
        "verified": when.strftime("%Y-%m-%d"),
        "badge": "badges/%s.svg" % project["slug"],
        "plaque": "badges/%s-plaque.svg" % project["slug"],
    }


def verify_local(project, checkout_dir, when=None):
    """Verify one project from a local checkout and build its entry."""
    when = when or datetime.now()
    entry = base_entry(project, when)
    audit_root = os.path.join(checkout_dir, project["audit_path"])
    if not os.path.isdir(audit_root):
        entry.update(
            status="recheck",
            score=None,
            skills=0,
            failures=0,
            note="The audit path %s was not found in the repo."
            % project["audit_path"],
        )
        return entry
    try:
        summary = summarize(audit_local(audit_root))
    except Exception as exc:  # an audit that blows up is a recheck
        summary = {
            "status": "recheck",
            "score": None,
            "skills": 0,
            "failures": 0,
            "note": "The audit could not be completed: %s" % exc,
        }
    entry.update(summary)
    return entry


def fetch_repo(repo_url, dest):
    """Shallow clone a public repo. Raises on any failure."""
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, dest],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )


def verify_project(project, workdir, when=None):
    """Clone one listed repo and verify it."""
    when = when or datetime.now()
    dest = os.path.join(workdir, project["slug"])
    try:
        fetch_repo(project["repo"], dest)
    except Exception:
        entry = base_entry(project, when)
        entry.update(
            status="recheck",
            score=None,
            skills=0,
            failures=0,
            note="The repo could not be cloned for this check.",
        )
        return entry
    return verify_local(project, dest, when)


# ---------------------------------------------------------------------------
# The images. Passing projects reuse the tool's own badge and plaque
# geometry, so the live images and the earned snapshot files are one
# design. The recheck variants keep the same frames in muted grey.
# ---------------------------------------------------------------------------


def recheck_badge_svg():
    """The small badge in its recheck state: same frame, grey pulse."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="28" '
        'viewBox="0 0 256 28">'
        '<rect width="256" height="28" rx="6" fill="%s" stroke="%s"/>'
        '<polyline points="10,14 19,14 23,6 28,22 32,14 43,14" fill="none" '
        'stroke="%s" stroke-width="2" stroke-linejoin="round" '
        'stroke-linecap="round"/>'
        '<line x1="52" y1="6" x2="52" y2="22" stroke="%s" stroke-width="1"/>'
        '<text x="62" y="11" font-family="%s" font-size="7.5" '
        'letter-spacing="1.5" fill="%s">AUDITED BY</text>'
        '<text x="62" y="23" font-family="%s" font-size="10.5" '
        'font-weight="600" fill="%s">SKILLDOCTOR</text>'
        '<line x1="150" y1="6" x2="150" y2="22" stroke="%s" stroke-width="1"/>'
        '<text x="162" y="18" font-family="%s" font-size="10" '
        'fill="%s">RECHECK</text>'
        "</svg>"
        % (
            INK,
            EDGE,
            MUTED,
            DIVIDER,
            FONT,
            MUTED,
            FONT,
            MUTED,
            DIVIDER,
            FONT,
            MUTED,
        )
    )


def recheck_plaque_svg(when):
    """The large plaque in its recheck state: same frame, grey throughout."""
    sub_line = "Not passing · %s" % when.strftime("%B %Y")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="560" height="148" '
        'viewBox="0 0 560 148">'
        '<rect width="560" height="148" rx="16" fill="%s" stroke="%s"/>'
        '<rect x="6" y="6" width="548" height="136" rx="12" fill="none" '
        'stroke="%s" stroke-opacity="0.45"/>'
        '<polyline points="36,74 56,74 68,42 82,106 92,74 132,74" fill="none" '
        'stroke="%s" stroke-width="5" stroke-linejoin="round" '
        'stroke-linecap="round"/>'
        '<line x1="156" y1="34" x2="156" y2="114" stroke="%s" stroke-width="1"/>'
        '<text x="180" y="52" font-family="%s" font-size="15" '
        'letter-spacing="3" fill="%s">SKILLDOCTOR AUDITED</text>'
        '<text x="180" y="92" font-family="%s" font-size="30" '
        'font-weight="600" fill="%s">Recheck needed</text>'
        '<text x="180" y="122" font-family="%s" font-size="15" '
        'fill="%s">%s</text>'
        "</svg>"
        % (
            INK,
            EDGE,
            MUTED,
            MUTED,
            DIVIDER,
            FONT,
            MUTED,
            FONT,
            MUTED,
            FONT,
            MUTED,
            sub_line,
        )
    )


def badge_for(entry, when):
    if entry["status"] == "current":
        return sd.badge_svg(
            score=entry["score"], month=when.strftime("%b %Y").upper()
        )
    return recheck_badge_svg()


def plaque_for(entry, when):
    if entry["status"] == "current":
        sub_line = "%d skills · 0 failures · %s" % (
            entry["skills"],
            when.strftime("%B %Y"),
        )
        return sd.plaque_svg("Health %d / 100" % entry["score"], sub_line)
    return recheck_plaque_svg(when)


# ---------------------------------------------------------------------------
# The page. Pre-rendered on every run, no client side framework: what
# the generator writes is what the visitor gets.
# ---------------------------------------------------------------------------

PAGE_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; background: #141414; color: #F2EFE9;
  font-family: Verdana, Geneva, sans-serif; line-height: 1.55;
}
.wrap { max-width: 880px; margin: 0 auto; padding: 48px 20px 64px; }
.eyebrow {
  color: #C9A35F; letter-spacing: 3px; font-size: 13px;
  text-transform: uppercase; margin: 0 0 8px;
}
h1 { font-size: 34px; margin: 0 0 12px; font-weight: 600; }
.lede { color: #8A8680; font-size: 15px; margin: 0 0 40px; max-width: 640px; }
.project {
  border: 1px solid #2E2E2E; border-radius: 16px;
  padding: 28px; margin: 0 0 28px; background: #181818;
}
.project img.plaque { max-width: 100%; height: auto; display: block; }
.project h2 { font-size: 20px; margin: 20px 0 6px; font-weight: 600; }
.project h2 a { color: #F2EFE9; text-decoration: none; }
.project h2 a:hover { color: #C9A35F; }
.stats { color: #8A8680; font-size: 14px; margin: 0 0 12px; }
.links { font-size: 14px; margin: 0 0 16px; }
.links a { color: #C9A35F; text-decoration: none; }
.links a:hover { text-decoration: underline; }
.pill {
  display: inline-block; border: 1px solid #C9A35F; color: #C9A35F;
  border-radius: 999px; padding: 1px 10px; font-size: 12px;
  letter-spacing: 1.5px; text-transform: uppercase; margin-right: 10px;
}
.pill.recheck { border-color: #8A8680; color: #8A8680; }
.note { color: #8A8680; font-size: 14px; margin: 0 0 12px; }
details { font-size: 13px; color: #8A8680; }
details summary { cursor: pointer; color: #C9A35F; }
pre {
  background: #101010; border: 1px solid #2E2E2E; border-radius: 8px;
  padding: 12px; overflow-x: auto; color: #F2EFE9; font-size: 12px;
}
footer { color: #8A8680; font-size: 13px; margin-top: 48px; }
footer a { color: #C9A35F; text-decoration: none; }
footer a:hover { text-decoration: underline; }
"""


def render_project(entry):
    name = html.escape(entry["name"])
    repo = html.escape(entry["repo"])
    homepage = html.escape(entry["homepage"])
    plaque = html.escape(entry["plaque"])
    badge_url = "%s/%s" % (SITE_URL, entry["badge"])
    plaque_url = "%s/%s" % (SITE_URL, entry["plaque"])
    if entry["status"] == "current":
        pill = '<span class="pill">Current</span>'
        stats = "Health %d of 100 · %d skills · Verified %s" % (
            entry["score"],
            entry["skills"],
            entry["verified"],
        )
    else:
        pill = '<span class="pill recheck">Recheck needed</span>'
        stats = "Last checked %s" % entry["verified"]
    note = ""
    if entry.get("note"):
        note = '<p class="note">%s</p>' % html.escape(entry["note"])
    snippet = (
        "[![Audited by SkillDoctor](%s)](%s/)\n\n"
        '<a href="%s/"><img src="%s" alt="SkillDoctor audited plaque" '
        'width="560"></a>' % (badge_url, SITE_URL, SITE_URL, plaque_url)
    )
    return (
        '<section class="project">\n'
        '<a href="%s"><img class="plaque" src="%s" '
        'alt="%s audited plaque" width="560"></a>\n'
        "<h2><a href=\"%s\">%s</a></h2>\n"
        '<p class="stats">%s</p>\n'
        "%s"
        '<p class="links">%s<a href="%s">Homepage</a> · '
        '<a href="%s">Repository</a></p>\n'
        "<details><summary>The live snippet for this project</summary>\n"
        "<pre>%s</pre></details>\n"
        "</section>"
        % (
            repo,
            plaque,
            name,
            repo,
            name,
            stats,
            note,
            pill,
            homepage,
            repo,
            html.escape(snippet),
        )
    )


def render_index(entries, when):
    projects = "\n".join(render_project(entry) for entry in entries)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>The SkillDoctor registry</title>\n"
        "<style>%s</style>\n</head>\n<body>\n"
        '<div class="wrap">\n<header>\n'
        '<p class="eyebrow">SkillDoctor</p>\n'
        "<h1>The registry</h1>\n"
        '<p class="lede">Projects listed here passed a SkillDoctor audit, '
        "and this page is the proof: anyone can paste a badge, so the "
        "badges here are live. A scheduled job re-audits every listed "
        "repo each day and regenerates the images from the latest "
        "result. A project that stops passing flips to a grey recheck "
        "plaque until it passes again.</p>\n"
        "</header>\n<main>\n%s\n</main>\n"
        "<footer>\n<p>Run by <a href=\"https://github.com/Dongdarealest/"
        'skilldoctor">SkillDoctor</a>. How listing and verification work: '
        '<a href="https://github.com/Dongdarealest/skilldoctor/blob/main/'
        'REGISTRY.md">REGISTRY.md</a>. The machine readable state is '
        '<a href="registry.json">registry.json</a>. '
        "Last rebuilt %s.</p>\n</footer>\n</div>\n</body>\n</html>\n"
        % (PAGE_CSS, projects, when.strftime("%Y-%m-%d"))
    )


# ---------------------------------------------------------------------------
# The build itself.
# ---------------------------------------------------------------------------


def load_projects(path=PROJECTS_FILE):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["projects"]


def write_site(entries, when, docs_dir=DOCS_DIR):
    badges_dir = os.path.join(docs_dir, "badges")
    os.makedirs(badges_dir, exist_ok=True)
    for entry in entries:
        badge_path = os.path.join(docs_dir, entry["badge"])
        with open(badge_path, "w", encoding="utf-8") as fh:
            fh.write(badge_for(entry, when) + "\n")
        plaque_path = os.path.join(docs_dir, entry["plaque"])
        with open(plaque_path, "w", encoding="utf-8") as fh:
            fh.write(plaque_for(entry, when) + "\n")
    state = {"generated": when.strftime("%Y-%m-%d"), "projects": entries}
    with open(os.path.join(docs_dir, "registry.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(docs_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(entries, when))


def main():
    when = datetime.now()
    projects = load_projects()
    entries = []
    with tempfile.TemporaryDirectory() as workdir:
        for project in projects:
            entry = verify_project(project, workdir, when)
            entries.append(entry)
            print(
                "%s: %s (score %s, %d skills, %d failures)"
                % (
                    entry["slug"],
                    entry["status"],
                    entry["score"],
                    entry["skills"],
                    entry["failures"],
                )
            )
    write_site(entries, when)
    print("Registry site written to %s" % DOCS_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
