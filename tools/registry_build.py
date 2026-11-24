#!/usr/bin/env python3
"""Build the live SkillClinic registry site.

The registry enrolls itself. A project that wants a listing pastes a
snippet whose image address carries its own GitHub identity:

    https://skilldoctor-badges.vercel.app/badges/<owner>--<repo>.svg

Each run of this script:

  1. Searches GitHub code search for the badge address, reads the
     owner and repo out of every matched address, and enrolls the
     repos that are not listed yet. Entries that were enrolled this
     way and whose badge address is no longer found are dropped, and
     their generated images are removed.
  2. Re-audits every listed repo from a fresh shallow clone. One
     scoring rule for everyone: the score is the health score the
     audit reports for the project's audit path.
  3. Regenerates the GitHub Pages site under docs/: the registry page,
     the machine readable state, and one badge and plaque per project,
     plus the plain audited mark that carries no score.

A project whose latest audit passes wears its current score. A
project whose latest audit fails, or that cannot be cloned or
audited, flips to the grey recheck design until it passes again. A
project with no auditable skills at all wears the neutral design:
the standard gold frame saying there are no skills to audit, with
no score. Sample data is never scored, here or anywhere else.

Run by hand with

    python3 tools/registry_build.py

or daily by .github/workflows/registry-verify.yml. Discovery needs a
GitHub token (REGISTRY_SEARCH_TOKEN if the maintainers set one, else
the workflow token); without one it
is skipped and the listed projects are simply re-verified. The audit
and bookkeeping steps are factored so local folders and fixture data
can drive them in tests, with no network involved. Standard library
only, like the tool it serves.
"""

import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import skillclinic as sd

PROJECTS_FILE = os.path.join(ROOT, "registry", "projects.json")
DOCS_DIR = os.path.join(ROOT, "docs")
SITE_URL = "https://dongdarealest.github.io/skillclinic"
# The one canonical badge address. Snippets, previews and the docs
# build every badge URL from this base. The endpoint behind it always
# answers with a real image (the pending design for a repo that has
# not been audited yet), so a pasted badge never renders as a broken
# image. The static files under docs/badges/ are data mirrors of the
# same images, regenerated on every run.
BADGE_BASE_URL = "https://skilldoctor-badges.vercel.app/badges/"
BADGE_MARKER = "skilldoctor-badges.vercel.app/badges/"
LEGACY_BADGE_MARKER = "dongdarealest.github.io/skillclinic/badges/"
GENERIC_BADGE = "audited.svg"
GENERIC_PLAQUE = "audited-plaque.svg"

INK = "#141414"
EDGE = "#2E2E2E"
DIVIDER = "#3A3A3A"
GOLD = "#C9A35F"
BONE = "#F2EFE9"
MUTED = "#8A8680"
FONT = sd.BADGE_FONT


# ---------------------------------------------------------------------------
# The audit. One rule for every project, listed or discovered: audit
# the project's audit path (a folder inside the repo, or the repo root
# for discovered projects, where the tool finds skills recursively)
# and take the health score the audit reports for that path.
# ---------------------------------------------------------------------------


def audit_local(audit_root):
    """Audit one local folder and return the machine readable payload."""
    reports, samples = sd.scan_all([audit_root])
    return sd.build_payload(reports, [audit_root], samples)


def summarize(payload):
    """Fold one audit payload into a project status.

    Three states. Current: at least one scored skill and none fail,
    so the project wears its score. Neutral: zero scored skills, the
    project carries no auditable skills at all (sample data under
    examples/, fixtures/ or testdata/ folders is listed as not
    audited and never counts), so it wears the plain design with no
    score. Recheck: scored skills with failures, so an old score is
    never silently kept. Every summary carries the state explicitly
    alongside the status, and the count of unaudited samples.
    """
    summary = payload["summary"]
    samples = payload.get("not_audited_samples") or []
    if summary["total"] == 0:
        return {
            "status": "neutral",
            "state": "neutral",
            "score": None,
            "skills": 0,
            "failures": 0,
            "samples": len(samples),
            "note": (
                "Sample data only, listed as not audited."
                if samples
                else "No skills found at the audit path."
            ),
        }
    if summary["fail"] > 0:
        return {
            "status": "recheck",
            "state": "recheck",
            "score": None,
            "skills": summary["total"],
            "failures": summary["fail"],
            "samples": len(samples),
            "note": "%d skill(s) currently fail the audit." % summary["fail"],
        }
    return {
        "status": "current",
        "state": "current",
        "score": payload["health_score"],
        "skills": summary["total"],
        "failures": 0,
        "samples": len(samples),
        "note": None,
    }


# ---------------------------------------------------------------------------
# Discovery. Code search finds files that carry a badge address; the
# owner and repo are read straight out of the address itself, so the
# link a project pasted is its enrollment. The search step sits behind
# a seam (any callable returning text blobs) so tests never touch the
# network.
# ---------------------------------------------------------------------------

IDENTITY_RE = re.compile(
    r"(?:skilldoctor-badges[.]vercel[.]app|"
    r"dongdarealest[.]github[.]io/skillclinic)/badges/"
    r"([A-Za-z0-9_.-]+?)--([A-Za-z0-9_.-]+?)(?:-plaque)?[.]svg"
)


def parse_identities(texts):
    """Extract {(owner, repo)} identities from badge addresses in text.

    Keys are lowercased pairs (GitHub names are case insensitive); the
    values keep the spelling first seen, for display and file names.
    The plain audited mark has no double hyphen and never matches, so
    it enrolls nothing, as documented.
    """
    found = {}
    for text in texts:
        for owner, repo in IDENTITY_RE.findall(text or ""):
            found.setdefault((owner.lower(), repo.lower()), (owner, repo))
    return found


def _search_marker_texts(marker, token):
    """Text blobs code search reports for one badge marker."""
    query = urllib.parse.urlencode({"q": '"%s"' % marker, "per_page": 100})
    texts = []
    page = 1
    while page <= 10:
        url = "https://api.github.com/search/code?%s&page=%d" % (query, page)
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer %s" % token,
                "Accept": "application/vnd.github.text-match+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
        items = data.get("items", [])
        for item in items:
            fragments = [
                match.get("fragment", "")
                for match in item.get("text_matches", [])
            ]
            if fragments:
                texts.extend(fragments)
            elif item.get("url"):
                texts.append(fetch_file_text(item["url"], token))
        if len(items) < 100:
            break
        page += 1
    return texts


def github_search_texts(token):
    """Return the text blobs code search reports for the badge markers.

    Searches the canonical endpoint marker and the legacy Pages
    marker, so badges pasted under either address enroll. Uses the
    text match fragments when GitHub sends them and falls back to
    fetching a matched file's contents when it does not. Raises on
    any HTTP failure, so the caller can skip discovery for this run
    instead of mistaking an outage for an empty registry.
    """
    texts = []
    for marker in (BADGE_MARKER, LEGACY_BADGE_MARKER):
        texts.extend(_search_marker_texts(marker, token))
    return texts


def fetch_file_text(api_url, token):
    """Fetch one matched file's decoded contents through the API."""
    import base64

    request = urllib.request.Request(
        api_url,
        headers={
            "Authorization": "Bearer %s" % token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    if data.get("encoding") == "base64" and data.get("content"):
        return base64.b64decode(data["content"]).decode("utf-8", "replace")
    return ""


def discover_identities(token, search_fn=None):
    """Find badge wearers, or return None when discovery cannot run.

    None means skip: no token, or the search itself failed. An empty
    dict is a real result (nobody found) and is not the same thing.
    """
    if not token:
        return None
    search_fn = search_fn or (lambda: github_search_texts(token))
    try:
        texts = search_fn()
    except Exception:
        return None
    return parse_identities(texts)


def slug_identity(slug):
    """The lowercased (owner, repo) key a slug was built from."""
    owner, _, repo = slug.partition("--")
    return (owner.lower(), repo.lower())


def reconcile_projects(projects, identities):
    """Apply one discovery result to the project list.

    Maintainer listed projects are always kept. Discovered projects
    are kept only while their badge address is still found, and new
    identities are enrolled. Returns (kept_projects, dropped_slugs).
    When identities is None, discovery did not run and nothing moves.
    """
    if identities is None:
        return list(projects), []
    kept = []
    dropped = []
    known = set()
    for project in projects:
        key = slug_identity(project["slug"])
        if project.get("source") == "discovered" and key not in identities:
            dropped.append(project["slug"])
            continue
        kept.append(project)
        known.add(key)
    for key, (owner, repo) in sorted(identities.items()):
        if key in known:
            continue
        repo_url = "https://github.com/%s/%s" % (owner, repo)
        kept.append(
            {
                "slug": "%s--%s" % (owner, repo),
                "name": "%s/%s" % (owner, repo),
                "repo": repo_url,
                "audit_path": ".",
                "homepage": repo_url,
                "source": "discovered",
            }
        )
    return kept, dropped


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
            state="recheck",
            score=None,
            skills=0,
            failures=0,
            samples=0,
            note="The audit path %s was not found in the repo."
            % project["audit_path"],
        )
        return entry
    try:
        summary = summarize(audit_local(audit_root))
    except Exception as exc:  # an audit that blows up is a recheck
        summary = {
            "status": "recheck",
            "state": "recheck",
            "score": None,
            "skills": 0,
            "failures": 0,
            "samples": 0,
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
            state="recheck",
            score=None,
            skills=0,
            failures=0,
            samples=0,
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
        'font-weight="600" fill="%s">SKILLCLINIC</text>'
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
        'letter-spacing="3" fill="%s">SKILLCLINIC AUDITED</text>'
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


def generic_plaque_svg():
    """The generic plaque: the design every earned plaque follows.

    The same artwork as the repo asset assets/audited-plaque.svg,
    generated here so the site copy can never drift from the design
    the tool itself writes.
    """
    return sd.plaque_svg(
        "The mark of a checked skill",
        "Earned by passing the audit. Verified in the registry.",
        fit=True,
    )


def neutral_badge_svg():
    """The small badge in its neutral state: the standard gold design,
    its segment reading NO SKILLS instead of a score. Same geometry as
    the personalized badge the tool writes, so the endpoint port of
    this design renders byte for byte the same image."""
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
        'font-weight="600" fill="%s">SKILLCLINIC</text>'
        '<line x1="150" y1="6" x2="150" y2="22" stroke="%s" stroke-width="1"/>'
        '<text x="162" y="18" font-family="%s" font-size="10" '
        'fill="%s">NO SKILLS</text>'
        "</svg>"
        % (
            INK,
            EDGE,
            GOLD,
            DIVIDER,
            FONT,
            MUTED,
            FONT,
            BONE,
            DIVIDER,
            FONT,
            GOLD,
        )
    )


def neutral_plaque_svg(entry):
    """The large plaque in its neutral state: the standard gold design
    saying there is nothing to audit, and why."""
    if entry.get("samples"):
        sub_line = "Sample fixtures only, listed as not audited."
    else:
        sub_line = "No skills found in this repo."
    return sd.plaque_svg("No skills to audit", sub_line)


def entry_state(entry):
    """The registry state of an entry: current, neutral or recheck.

    Entries carry the state explicitly; the status field predates the
    neutral state, so older entries without a state fall back to it.
    """
    return entry.get("state") or entry.get("status")


def badge_for(entry, when):
    state = entry_state(entry)
    if state == "current":
        return sd.badge_svg(
            score=entry["score"], month=when.strftime("%b %Y").upper()
        )
    if state == "neutral":
        return neutral_badge_svg()
    return recheck_badge_svg()


def plaque_for(entry, when):
    state = entry_state(entry)
    if state == "current":
        sub_line = "%d skills · 0 failures · %s" % (
            entry["skills"],
            when.strftime("%B %Y"),
        )
        return sd.plaque_svg("Health %d / 100" % entry["score"], sub_line)
    if state == "neutral":
        return neutral_plaque_svg(entry)
    return recheck_plaque_svg(when)


# ---------------------------------------------------------------------------
# The page. Pre-rendered on every run: what the generator writes is
# what the visitor gets, apart from one small script that builds a
# snippet from a repo name the visitor types and points the badge and
# plaque previews at that repo's own addresses.
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
h2 { font-size: 20px; margin: 0 0 10px; font-weight: 600; }
.lede { color: #8A8680; font-size: 15px; margin: 0 0 40px; max-width: 640px; }
.generator, .project {
  border: 1px solid #2E2E2E; border-radius: 16px;
  padding: 28px; margin: 0 0 28px; background: #181818;
}
.generator p { color: #8A8680; font-size: 14px; margin: 0 0 16px; }
.generator .row { display: flex; gap: 10px; flex-wrap: wrap; }
.generator input {
  flex: 1 1 320px; background: #101010; border: 1px solid #2E2E2E;
  border-radius: 8px; color: #F2EFE9; padding: 10px 12px; font-size: 14px;
  font-family: inherit;
}
.generator button {
  background: #141414; border: 1px solid #C9A35F; color: #C9A35F;
  border-radius: 8px; padding: 10px 18px; font-size: 14px;
  font-family: inherit; cursor: pointer; letter-spacing: 1px;
}
.generator button:hover { background: #C9A35F; color: #141414; }
.generator label { display: block; font-size: 13px; color: #8A8680; margin: 16px 0 6px; }
.project img.plaque { max-width: 100%; height: auto; display: block; }
.project h2 { margin: 20px 0 6px; }
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
.pill.neutral { border-color: #F2EFE9; color: #F2EFE9; }
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
.hero .brand {
  display: flex; align-items: center; gap: 12px;
  font-size: 22px; font-weight: 600; letter-spacing: 1px; margin: 0 0 20px;
}
.hero h1 { font-size: 30px; line-height: 1.3; margin: 0 0 12px; }
.hero .sub { color: #8A8680; font-size: 15px; max-width: 640px; margin: 0 0 26px; }
img.plaque { max-width: 100%; height: auto; display: block; }
.preview { border-top: 1px solid #2E2E2E; margin-top: 22px; padding-top: 20px; }
.preview .preview-label { font-size: 13px; color: #8A8680; margin: 0 0 12px; }
.preview img.badge { display: block; margin: 0 0 14px; }
section.block { margin: 0 0 28px; }
section.block > p { color: #8A8680; font-size: 14px; }
.steps { list-style: none; counter-reset: step; padding: 0; margin: 0; }
.steps li {
  counter-increment: step; position: relative;
  padding: 2px 0 16px 52px; font-size: 14px; color: #8A8680;
}
.steps li::before {
  content: counter(step); position: absolute; left: 0; top: 0;
  width: 34px; height: 34px; border: 1px solid #C9A35F; border-radius: 50%;
  color: #C9A35F; text-align: center; line-height: 34px; font-size: 15px;
}
.steps li strong { color: #F2EFE9; display: block; font-size: 15px; margin-bottom: 2px; }
.checks { padding-left: 18px; color: #8A8680; font-size: 14px; margin: 0 0 12px; }
.checks li { margin-bottom: 8px; }
.checks li strong { color: #F2EFE9; }
.honesty {
  border: 1px solid #2E2E2E; border-radius: 16px;
  padding: 28px; margin: 0 0 28px; background: #181818;
}
.honesty p { color: #8A8680; font-size: 14px; margin: 0 0 10px; }
.honesty p:last-child { margin-bottom: 0; }
.honesty strong { color: #F2EFE9; }
section.block a { color: #C9A35F; text-decoration: none; }
section.block a:hover { text-decoration: underline; }
"""

HERO_HTML = """
<header class="hero">
  <p class="brand"><svg width="46" height="28" viewBox="0 0 46 28" aria-hidden="true"><polyline points="2,14 11,14 15,6 20,22 24,14 42,14" fill="none" stroke="#C9A35F" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>SkillClinic</p>
  <h1>A live trust mark for AI skills. Wear the badge, get audited every day, and your score is always the true one.</h1>
  <p class="sub">SkillClinic audits the skills your AI runs, the files a host loads into every conversation. Projects that pass earn the plaque below, served live from this registry and re-checked daily.</p>
  <p><img class="plaque" src="__BADGE_BASE_URL__audited-plaque.svg" onerror="this.onerror=null;this.src='badges/audited-plaque.svg'" alt="The SkillClinic audited plaque: the mark of a checked skill" width="560"></p>
</header>
"""

GENERATOR_HTML = """
<section class="generator">
  <h2>Get your live badge</h2>
  <p>Type your GitHub repo and this page builds your personal snippet.
  Paste it into your README and that is the whole enrollment: the daily
  verification run searches GitHub for the badge address, finds your
  repo, audits it and lists it here with its real score.</p>
  <div class="row">
    <input id="repo-input" type="text" placeholder="owner/repo or https://github.com/owner/repo" aria-label="GitHub repository">
    <button id="repo-go" type="button">Build my snippet</button>
  </div>
  <p class="note" id="repo-error" hidden>That does not look like a GitHub owner and repo yet.</p>
  <div class="preview">
    <p class="preview-label">This is what your badge and plaque look like. Type your repo above and the preview switches to your personal addresses.</p>
    <img class="badge" id="preview-badge" src="__BADGE_BASE_URL__audited.svg" onerror="this.onerror=null;this.src='badges/audited.svg'" alt="Your SkillClinic badge, as it will appear" height="28">
    <img class="plaque" id="preview-plaque" src="__BADGE_BASE_URL__audited-plaque.svg" onerror="this.onerror=null;this.src='badges/audited-plaque.svg'" alt="Your SkillClinic plaque, as it will appear" width="560">
    <p class="note">Your address answers with this pending design from the moment you paste it, never a broken image. At the next daily verification run the same address switches to your true score.</p>
  </div>
  <div id="repo-out" hidden>
    <label for="badge-snippet">The badge, for badge rows (Markdown)</label>
    <pre id="badge-snippet"></pre>
    <label for="plaque-snippet">The plaque, for a place of honor (HTML)</label>
    <pre id="plaque-snippet"></pre>
    <p class="note">Your badge is live at this address right away,
    showing the pending design. At the next daily verification run your
    repo is audited and the same address switches to your true score.
    GitHub code search indexing can delay discovery of a brand new
    badge by some hours.</p>
  </div>
</section>
"""

HOW_HTML = """
<section class="block">
  <h2>How it works</h2>
  <ol class="steps">
    <li><strong>Get your personal link</strong>
    Type your repo in the generator above and copy the snippet. The badge address carries your own GitHub owner and repo, and that address is the whole enrollment: no account, no submission form.</li>
    <li><strong>Paste it into your README</strong>
    The small badge fits a badge row; the plaque takes a place of honor. Both are live images served from your badge address, not files in your repo, so what readers see is always the latest result.</li>
    <li><strong>Get audited every day</strong>
    A scheduled run searches GitHub for the badge address, audits the skills of every repo it finds, and regenerates each badge at its true score. Slip below the standard and the badge flips to a grey recheck state until the skills pass again.</li>
  </ol>
</section>
"""

CHECKS_HTML = """
<section class="block">
  <h2>What the audit checks</h2>
  <p>Every listed project is re-audited with the current SkillClinic release. The audit reads every skill in the project, and every file bundled with it, and checks:</p>
  <ul class="checks">
    <li><strong>Validity and spec limits.</strong> Frontmatter and required fields, names that match their folders, names within 64 characters and descriptions within 1,024.</li>
    <li><strong>Security.</strong> Instruction override and data exfiltration language, credential store access, destructive shell commands, long opaque blobs, and hidden Unicode: bidi controls, zero width characters and tag characters that can hide instructions from a human reader.</li>
    <li><strong>Bundled files.</strong> The scripts and references inside a skill folder are scanned with the same patterns. Anything the tool cannot scan is reported as not audited, never silently passed.</li>
    <li><strong>Token cost, split honestly.</strong> The always-on cost of names and descriptions, which a host loads into every conversation, reported separately from the per-use cost of skill bodies.</li>
    <li><strong>Conflicts.</strong> Duplicate skill names and near duplicate descriptions that could make a host load the wrong skill.</li>
  </ul>
  <p>The evidence behind the checks is <a href="https://github.com/Dongdarealest/skillclinic/blob/main/AUDIT.md">the audit of 777 public skills</a>, and the listing rules live in <a href="https://github.com/Dongdarealest/skillclinic/blob/main/REGISTRY.md">REGISTRY.md</a>.</p>
</section>
"""

EXAMPLES_INTRO = """
<section class="block">
  <h2>Verified entries</h2>
  <p>These projects wear the live plaque today, rendered exactly as it appears on their READMEs.</p>
</section>
"""

HONESTY_HTML = """
<section class="honesty">
  <h2>The honest part</h2>
  <p><strong>The picture alone proves nothing.</strong> Anyone can copy an image into a README, so the proof is the entry on this page, generated by the registry itself from its own audit. A badge that is not listed here is just a picture.</p>
  <p>Entries are re-verified daily, so a score on this page is the latest result, not a lifetime grade. A project that stops passing shows the recheck design until it passes again. And until a repo is first audited, its address shows a pending design: never a broken image, and never a score it has not earned.</p>
  <p>A project that carries no auditable skills at all is listed as <strong>No skills</strong>, in the plain gold design with no score: sample data under examples, fixtures or testdata folders is listed as not audited and never counts toward one. Wearing the badge is not itself a result.</p>
  <p>Taking the badge address out of a README removes the listing at the next run, and discovery of a brand new badge can take some hours, because GitHub code search indexing lags behind.</p>
</section>
"""

GENERATOR_JS = """
(function () {
  var SITE = "https://dongdarealest.github.io/skillclinic";
  var BADGES = "__BADGE_BASE_URL__";
  function parseRepo(raw) {
    var s = raw.trim();
    s = s.replace(/^https?:\\/\\/github\\.com\\//, "").replace(/\\/$/, "").replace(/\\.git$/, "");
    var parts = s.split("/");
    if (parts.length !== 2) { return null; }
    var ok = /^[A-Za-z0-9_.-]+$/;
    if (!ok.test(parts[0]) || !ok.test(parts[1])) { return null; }
    return parts;
  }
  function setPreview(img, personal, generic) {
    img.onerror = function () {
      img.onerror = null;
      img.src = generic;
    };
    img.src = personal;
  }
  function updatePreviews(parts) {
    var badge = document.getElementById("preview-badge");
    var plaque = document.getElementById("preview-plaque");
    if (!parts) {
      badge.src = BADGES + "audited.svg";
      plaque.src = BADGES + "audited-plaque.svg";
      return;
    }
    var base = BADGES + parts[0] + "--" + parts[1];
    setPreview(badge, base + ".svg", "badges/audited.svg");
    setPreview(plaque, base + "-plaque.svg", "badges/audited-plaque.svg");
  }
  var input = document.getElementById("repo-input");
  input.addEventListener("input", function () {
    updatePreviews(parseRepo(input.value));
  });
  var button = document.getElementById("repo-go");
  button.addEventListener("click", function () {
    var parts = parseRepo(input.value);
    var out = document.getElementById("repo-out");
    var err = document.getElementById("repo-error");
    if (!parts) { out.hidden = true; err.hidden = false; return; }
    err.hidden = true;
    var base = BADGES + parts[0] + "--" + parts[1];
    document.getElementById("badge-snippet").textContent =
      "[![Audited by SkillClinic](" + base + ".svg)](" + SITE + "/)";
    document.getElementById("plaque-snippet").textContent =
      '<a href="' + SITE + '/"><img src="' + base +
      '-plaque.svg" alt="SkillClinic audited plaque" width="560"></a>';
    updatePreviews(parts);
    out.hidden = false;
  });
})();
"""


def render_project(entry):
    name = html.escape(entry["name"])
    repo = html.escape(entry["repo"])
    homepage = html.escape(entry["homepage"])
    plaque = html.escape(entry["plaque"])
    badge_url = "%s%s.svg" % (BADGE_BASE_URL, entry["slug"])
    plaque_url = "%s%s-plaque.svg" % (BADGE_BASE_URL, entry["slug"])
    if entry_state(entry) == "current":
        pill = '<span class="pill">Current</span>'
        stats = "Health %d of 100 · %d skills · Verified %s" % (
            entry["score"],
            entry["skills"],
            entry["verified"],
        )
    elif entry_state(entry) == "neutral":
        pill = '<span class="pill neutral">No skills</span>'
        stats = "No auditable skills · Verified %s" % entry["verified"]
    else:
        pill = '<span class="pill recheck">Recheck needed</span>'
        stats = "Last checked %s" % entry["verified"]
    note = ""
    if entry.get("note"):
        note = '<p class="note">%s</p>' % html.escape(entry["note"])
    snippet = (
        "[![Audited by SkillClinic](%s)](%s/)\n\n"
        '<a href="%s/"><img src="%s" alt="SkillClinic audited plaque" '
        'width="560"></a>' % (badge_url, SITE_URL, SITE_URL, plaque_url)
    )
    return (
        '<section class="project">\n'
        '<a href="%s"><img class="plaque" src="%s" '
        'onerror="this.onerror=null;this.src=\'%s\'" '
        'alt="%s audited plaque" width="560"></a>\n'
        "<h2><a href=\"%s\">%s</a></h2>\n"
        '<p class="stats">%s</p>\n'
        "%s"
        '<p class="links">%s<a href="%s">Homepage</a> · '
        '<a href="%s">Repository</a></p>\n'
        "<details><summary>This project's live badge and plaque</summary>\n"
        "<pre>%s</pre></details>\n"
        "</section>"
        % (
            repo,
            plaque_url,
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
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>SkillClinic registry: live badges for audited AI skills</title>",
        "<style>",
        PAGE_CSS,
        "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        HERO_HTML,
        "<main>",
        GENERATOR_HTML,
        HOW_HTML,
        CHECKS_HTML,
        EXAMPLES_INTRO + projects,
        HONESTY_HTML,
        "</main>",
        "<footer>",
        '<p>Run by <a href="https://github.com/Dongdarealest/skillclinic">SkillClinic</a>. '
        "How listing and verification work: "
        '<a href="https://github.com/Dongdarealest/skillclinic/blob/main/REGISTRY.md">REGISTRY.md</a>. '
        'The machine readable state is <a href="registry.json">registry.json</a>. '
        "Last rebuilt " + when.strftime("%Y-%m-%d") + ".</p>",
        "</footer>",
        "</div>",
        "<script>",
        GENERATOR_JS,
        "</script>",
        "</body>",
        "</html>",
        "",
    ]
    page = "\n".join(parts)
    return page.replace("__BADGE_BASE_URL__", BADGE_BASE_URL)


# ---------------------------------------------------------------------------
# The build itself.
# ---------------------------------------------------------------------------


def load_projects(path=PROJECTS_FILE):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["projects"]


def save_projects(projects, path=PROJECTS_FILE):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"projects": projects}, fh, indent=2)
        fh.write("\n")


def write_site(entries, when, docs_dir=DOCS_DIR):
    badges_dir = os.path.join(docs_dir, "badges")
    os.makedirs(badges_dir, exist_ok=True)
    expected = {GENERIC_BADGE, GENERIC_PLAQUE}
    for entry in entries:
        expected.add(os.path.basename(entry["badge"]))
        expected.add(os.path.basename(entry["plaque"]))
    for name in os.listdir(badges_dir):
        if name.endswith(".svg") and name not in expected:
            os.remove(os.path.join(badges_dir, name))
    generic_path = os.path.join(badges_dir, GENERIC_BADGE)
    with open(generic_path, "w", encoding="utf-8") as fh:
        fh.write(sd.badge_svg() + "\n")
    generic_plaque_path = os.path.join(badges_dir, GENERIC_PLAQUE)
    with open(generic_plaque_path, "w", encoding="utf-8") as fh:
        fh.write(generic_plaque_svg() + "\n")
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
    token = (
        os.environ.get("REGISTRY_SEARCH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
    )
    identities = discover_identities(token)
    projects, dropped = reconcile_projects(projects, identities)
    if identities is not None:
        save_projects(projects)
        for slug in dropped:
            print("dropped: %s (badge no longer found)" % slug)
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
