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
