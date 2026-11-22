#!/usr/bin/env python3
"""Build the live SkillDoctor registry site.

The registry enrolls itself. A project that wants a listing pastes a
snippet whose image address carries its own GitHub identity:

    https://dongdarealest.github.io/skilldoctor/badges/<owner>--<repo>.svg

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
audited, flips to the grey recheck design until it passes again.

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

import skilldoctor as sd

PROJECTS_FILE = os.path.join(ROOT, "registry", "projects.json")
DOCS_DIR = os.path.join(ROOT, "docs")
SITE_URL = "https://dongdarealest.github.io/skilldoctor"
BADGE_MARKER = "dongdarealest.github.io/skilldoctor/badges/"
GENERIC_BADGE = "audited.svg"

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
    reports = sd.scan([audit_root])
    return sd.build_payload(reports, [audit_root])


def summarize(payload):
    """Fold one audit payload into a project status.

    Current means every audited skill passes. Anything else, a failing
    skill or no skills found at all, is a recheck.
    """
    summary = payload["summary"]
    if summary["total"] == 0:
        return {
            "status": "recheck",
            "score": None,
            "skills": 0,
            "failures": 0,
            "note": "No skills found at the audit path.",
        }
    if summary["fail"] > 0:
        return {
            "status": "recheck",
            "score": None,
            "skills": summary["total"],
            "failures": summary["fail"],
            "note": "%d skill(s) currently fail the audit." % summary["fail"],
        }
    return {
        "status": "current",
        "score": payload["health_score"],
        "skills": summary["total"],
        "failures": 0,
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
    r"dongdarealest\.github\.io/skilldoctor/badges/"
    r"([A-Za-z0-9_.-]+?)--([A-Za-z0-9_.-]+?)(?:-plaque)?\.svg"
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


def github_search_texts(token):
    """Return the text blobs code search reports for the badge marker.

    Uses the text match fragments when GitHub sends them and falls
    back to fetching a matched file's contents when it does not.
    Raises on any HTTP failure, so the caller can skip discovery for
    this run instead of mistaking an outage for an empty registry.
    """
    query = urllib.parse.urlencode({"q": '"%s"' % BADGE_MARKER, "per_page": 100})
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
# The page. Pre-rendered on every run: what the generator writes is
# what the visitor gets, apart from one small script that builds a
# snippet from a repo name the visitor types.
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
  <div id="repo-out" hidden>
    <label for="badge-snippet">The badge, for badge rows (Markdown)</label>
    <pre id="badge-snippet"></pre>
    <label for="plaque-snippet">The plaque, for a place of honor (HTML)</label>
    <pre id="plaque-snippet"></pre>
    <p class="note">Your badge activates at the next daily verification
    run. GitHub code search indexing can delay discovery of a brand new
    badge by some hours.</p>
  </div>
</section>
"""

GENERATOR_JS = """
(function () {
  var SITE = "https://dongdarealest.github.io/skilldoctor";
  function parseRepo(raw) {
    var s = raw.trim();
    s = s.replace(/^https?:\\/\\/github\\.com\\//, "").replace(/\\/$/, "").replace(/\\.git$/, "");
    var parts = s.split("/");
    if (parts.length !== 2) { return null; }
    var ok = /^[A-Za-z0-9_.-]+$/;
    if (!ok.test(parts[0]) || !ok.test(parts[1])) { return null; }
    return parts;
  }
  var button = document.getElementById("repo-go");
  button.addEventListener("click", function () {
    var parts = parseRepo(document.getElementById("repo-input").value);
    var out = document.getElementById("repo-out");
    var err = document.getElementById("repo-error");
    if (!parts) { out.hidden = true; err.hidden = false; return; }
    err.hidden = true;
    var base = SITE + "/badges/" + parts[0] + "--" + parts[1];
    document.getElementById("badge-snippet").textContent =
      "[![Audited by SkillDoctor](" + base + ".svg)](" + SITE + "/)";
    document.getElementById("plaque-snippet").textContent =
      '<a href="' + SITE + '/"><img src="' + base +
      '-plaque.svg" alt="SkillDoctor audited plaque" width="560"></a>';
    out.hidden = false;
  });
})();
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
        "<details><summary>This project's live badge and plaque</summary>\n"
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
        "badges here are live. Most projects got here by wearing the "
        "badge; a scheduled job searches GitHub each day for the badge "
        "address, audits what it finds, and regenerates these images "
        "from the latest result. A project that stops passing flips to "
        "a grey recheck plaque until it passes again, and one that "
        "takes the badge down is dropped.</p>\n"
        "</header>\n<main>\n%s\n%s\n</main>\n"
        "<footer>\n<p>Run by <a href=\"https://github.com/Dongdarealest/"
        'skilldoctor">SkillDoctor</a>. How listing and verification work: '
        '<a href="https://github.com/Dongdarealest/skilldoctor/blob/main/'
        'REGISTRY.md">REGISTRY.md</a>. The machine readable state is '
        '<a href="registry.json">registry.json</a>. '
        "Last rebuilt %s.</p>\n</footer>\n</div>\n"
        "<script>%s</script>\n</body>\n</html>\n"
        % (PAGE_CSS, GENERATOR_HTML, projects, when.strftime("%Y-%m-%d"), GENERATOR_JS)
    )


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
    expected = {GENERIC_BADGE}
    for entry in entries:
        expected.add(os.path.basename(entry["badge"]))
        expected.add(os.path.basename(entry["plaque"]))
    for name in os.listdir(badges_dir):
        if name.endswith(".svg") and name not in expected:
            os.remove(os.path.join(badges_dir, name))
    generic_path = os.path.join(badges_dir, GENERIC_BADGE)
    with open(generic_path, "w", encoding="utf-8") as fh:
        fh.write(sd.badge_svg() + "\n")
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
