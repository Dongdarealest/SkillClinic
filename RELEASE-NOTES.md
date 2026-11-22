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
