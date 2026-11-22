## v0.4.2

The auditor wears its own badge, and tells the truth with it. SkillDoctor's repo now carries its personal badge in the badge row, and because the repo ships no skills of its own, only the demo fixtures under examples/, its registry entry and plaque show a new registry state instead of a score. Two rules make that honest rather than convenient. First, sample data is never scored: skills found under examples/, fixtures/ or testdata/ folders during a scan are exhibits, not installations, so they are collected and listed in the report as not audited, and excluded from scoring, verdicts and conflict checks (point the tool straight at a sample folder and it still audits the contents, which is what the demo does). Auditing this repo root used to report three fixture skills and a health score of 42; it now reports zero skills audited and lists the three fixtures as not audited. Second, the registry gains a third state, neutral, beside current and recheck: a project with no auditable skills wears the standard gold design reading "No skills to audit", its small badge reading NO SKILLS, with no score invented for it, and registry entries now carry their state explicitly. The badge endpoint renders the neutral design as well, byte for byte the same image the generator writes. Ninety nine tests pass.

## v0.4.1

The registry site learned to introduce and illustrate the badge system, and the badge address moved to an endpoint that never answers with a broken image. The registry page now opens with the offer in plain words and the plaque at full size, shows live previews of the badge and plaque above the snippet boxes (type a repo and the previews switch to that repo's own addresses), walks through the three steps of enrollment and daily re-verification, lists what the audit actually checks, and closes with the honest limits in their own block: the picture alone proves nothing, the entry is the proof, entries are re-verified daily, and discovery of a new badge can lag while GitHub indexes it. Badge snippets and previews now build from one canonical base, the endpoint at skilldoctor-badges.vercel.app, which serves the pending design for a repo that has not been audited yet and the true score after the first verification; the static files under docs/badges/ remain as data mirrors, and the generator now emits the generic plaque alongside the generic badge. Discovery matches both address forms, the endpoint and the legacy Pages address, so badges pasted under either one enroll. Eighty six tests pass.

## v0.4.0

The badge went live, and the registry enrolls itself. A static plaque goes stale the moment a project changes its skills, so listed projects no longer wear a file committed to their own repo: their badge and plaque are served from the registry site on GitHub Pages (dongdarealest.github.io/skilldoctor), generated from the latest verification. Enrollment is one paste of a personal address that carries the wearer's own GitHub owner and repo (the registry page opens with a small generator that builds the snippet), and a scheduled workflow does the rest each day: it searches GitHub code search for the badge address, enrolls the repos it finds, re-audits every listed repo from a fresh clone, and republishes the registry. Keep passing and the plaque shows the current score; stop passing and it flips to a grey recheck design with no score, so an old result is never silently kept; take the badge down and the listing is dropped. One scoring rule now applies to everyone, the health score the audit reports for the project's audit path, which moves SkillPort's plaque from the weakest pack figure of 92 to the whole collection figure of 98. The registry data lives in registry/projects.json, the generator in tools/registry_build.py (its audit, parsing and bookkeeping steps run on local folders and fixtures, which is what its tests use), and the plain audited mark is served alongside, carrying no score and enrolling nothing. The static --write-badge files remain as a dated snapshot for announcements and offline use, and the audit report's closing lines now present the live route first. Seventy four tests pass.

## v0.3.9

The audit now ends with something worth showing. A passing audit earns the SkillDoctor badge, and this release gives the badge a real design (a gold pulse on ink, the project mark), a large plaque format for a place of honor at the top of a README, and a registry to make both mean something: the picture alone proves nothing, so listings in REGISTRY.md are added only after the maintainers re-run the audit and the results, file hashes included, match the submitted report. Run with --write-badge and a passing audit writes the personalized badge (score and month on its face), the plaque (health score, skill count and the zero failures line) and the machine report into the audited folder; a failing audit writes nothing and says why. The JSON report now carries the SHA-256 of every audited SKILL.md and the audit date. The conflict check also learned the shape of a skill collection: a skills/ source and its for-<target> distribution copies inside one tree are one skill, not a conflict, while genuine duplicates still flag, and template folders holding scaffolds are no longer audited as if they were installed skills. The installers now download skilldoctor.py and its checksum as release assets instead of raw files, so installs are countable, with the same one line command and the same checksum verification. Fifty three tests pass.

## v0.3.8

Six fixes from a careful external review (thank you, jcc2010; issue #18). The security scan now reads the whole SKILL.md, frontmatter included, because the description is the part a host loads into every conversation, and it also scans the other text files bundled in a skill folder; anything it cannot scan is listed in the report as not audited. Invisible Unicode characters (bidi controls, zero width characters, Unicode tag characters) are now a security error, since they can hide instructions a reader cannot see. Token cost is split honestly: name and description tokens are the always-on cost, body tokens load only when a skill runs, and the quarantine line frees the always-on figure. Names over 64 characters and descriptions over 1,024 characters are flagged against the spec limits, and the duplicate check no longer cries wolf over plugin caches: cached versions of one plugin, and skills namespaced by different plugins, are not conflicts. The installers now pin to the v0.3.8 release tag and verify a published SHA-256 (skilldoctor.py.sha256) before installing, refusing on any mismatch, and the README install lines point at the tag too. The audit page gains a correction note: its token figures counted whole files, which is total text size, not always-on cost. Forty two tests pass.

## v0.3.7

SkillDoctor now recognizes Muse skills. A Muse skill keeps its metadata in a skill.yaml file beside the SKILL.md, with no frontmatter by design, and the auditor used to fail every one of them for that missing block. It now reads the skill.yaml, takes the name and description from there, validates the name as snake_case, and runs the full security checks on the body as before. Claude format skills are audited exactly as they were.

## v0.3.5

The PyPI page shows the pictures now: the README images point at absolute addresses that PyPI can load, instead of relative ones only GitHub could resolve.

## v0.3.4

SkillDoctor is on PyPI as skillcheckup: pip install skillcheckup, then run the skilldoctor command. Publishing now runs through PyPI trusted publishing from this repo's release workflow, with no stored token anywhere.

## v0.3.3

Getting in is easier. The Windows installer now creates a real skilldoctor command instead of leaving you to call the file by hand, and every release from now on ships standalone executables for Windows, macOS and Linux, so no Python installation is needed at all. The README action example points at this version.

## v0.3.2

SkillDoctor now looks deeper. Real collections nest their skills a few folders down, and the scanner only looked one level deep, so pointing it at a collection root found nothing. It now walks the tree. The Windows install line also gets its own code block with a copy button, like the Mac and Linux one.

## v0.3.1

The report now speaks first and guides after. A plain language verdict opens every report, an empty scan explains where to point the tool instead of dead ending, and a failing audit ends with the exact next command and the tokens it frees. The README quick start moved up to where a new visitor looks for it. The CI matrix also drops Python 3.8, which current GitHub runners no longer provide, and runs each version to completion instead of cancelling the rest.

## v0.3.0

The report learned to grade and to advise. Every skill now carries a score out of 100 with a letter grade, the installation gets one health score, and most findings come with a fix line that says exactly what to change. Twenty two tests pass.

## v0.2.2

SkillDoctor now installs like a product instead of a download. One line puts a skilldoctor command on the machine, on Windows too, and the README leads with it. A pyproject.toml is in place so a PyPI release can follow without repackaging.

## v0.2.1

Two things a visitor asked for without words. The audit badge in the README is now shown rendered, the way it looks on a real repo, above the snippet you paste. And the repo now doubles as a GitHub Action, so a skill collection can audit itself on every push and fail the build when a skill fails.

## v0.2.0

Finding a bad skill is now only half the job. A new --quarantine-failed step moves every FAIL skill out of its host folder into a dated quarantine batch with a manifest, and --restore puts the last batch back. Nothing is deleted outright, and WARN verdicts are never moved. The README also gains an audited-by badge for skill authors. Twenty tests pass, including quarantine and restore round trips.

## v0.1.2

Two adoption fixes. The demo now travels with the file: download skilldoctor.py on its own and the ten second demo still works, with the example skills embedded as a fallback. And the Support section traded its bare links for proper sponsor buttons.

## v0.1.1

The README learned to show, not just tell: a designed masthead, and a picture of the real demo output near the top so a visitor sees the verdicts before reading a word of explanation.

# Release Notes

## v0.1.0 (2026-11-22)

First release of SkillDoctor, a zero dependency auditor for installed AI
skill files.

- Validity checks: frontmatter parsing, required fields, kebab-case
  names, and name to folder matching.
- Security checks: network shell pipes, credential store access,
  exfiltration language, prompt override phrases, opaque base64 blobs,
  and destructive shell commands.
- Conflict checks: duplicate skill names across host folders and
  near-duplicate descriptions.
- Token cost estimates per skill, plus the total always-on cost.
- Readable terminal report with OK, WARN, and FAIL verdicts, a --json
  mode for scripts and CI, and exit code 1 on any FAIL.
- Bundled examples and a --demo flag that audits them in seconds.
- Scans ~/.claude/skills, ~/.cursor/skills, ~/.codex/skills, and
  ~/.config/claude/skills by default, or any paths you pass in.
