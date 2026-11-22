<p align="center">
  <img src="https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/assets/masthead.png" alt="SkillDoctor: a checkup for the skills your AI runs" width="880">
</p>

<p align="center">
  <a href="https://github.com/Dongdarealest/skilldoctor/releases"><img src="https://img.shields.io/github/v/release/Dongdarealest/skilldoctor?style=flat-square&color=141414&label=release" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-141414?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-141414?style=flat-square" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/badge/dependencies-zero-141414?style=flat-square" alt="Zero dependencies">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=Dongdarealest.skilldoctor" alt="Visitors">
</p>

<p align="center">
  <a href="https://github.com/Dongdarealest/skilldoctor/blob/main/REGISTRY.md"><img src="https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/assets/audited-plaque.svg" alt="The SkillDoctor audited plaque: the mark of a checked skill" width="560"></a>
</p>

Projects that pass the audit earn this plaque and the badge further down. The picture alone proves nothing, and anyone can paste one: the proof is the entry in the registry, kept live at [dongdarealest.github.io/skilldoctor](https://dongdarealest.github.io/skilldoctor/) and described in [REGISTRY.md](REGISTRY.md). Listings are added only after the maintainers re-run the audit and the results match, and a daily re-audit keeps every listed badge honest after that.

Skills are instructions your AI loads and follows, often at the start of every conversation. Most people install them from repositories, gists, and chat messages without ever reading them. SkillDoctor reads them for you: one command audits every skill on your machine and gives each one a verdict.

<p align="center">
  <img src="https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/assets/demo.png" alt="SkillDoctor demo output: one clean skill passes, an invalid skill and a risky skill fail with reasons" width="880">
</p>

<p align="center"><em>The bundled demo: one clean skill passes, two fail, every failure with its reason.</em></p>

**The State of Public Skills:** we audited 777 skills from the six biggest public collections. One in three failed. [Read the audit](AUDIT.md).

## Quick start

With Python already set up, the familiar way works too:

```bash
pip install skillcheckup
```

One line installs a `skilldoctor` command on your machine:

```bash
curl -fsSL https://raw.githubusercontent.com/Dongdarealest/skilldoctor/v0.3.9/install.sh | bash
```

On Windows, in PowerShell:

```powershell
irm https://raw.githubusercontent.com/Dongdarealest/skilldoctor/v0.3.9/install.ps1 | iex
```

Both installers are pinned to the v0.3.9 release: they download `skilldoctor.py` and its published SHA-256 as assets of that release and check the two match before installing, refusing on any mismatch. The tool audits installers it would not trust, so its own had to pass.

Then it is just:

```bash
# Audit the skill folders on this machine
skilldoctor

# See it work in ten seconds on the bundled examples
skilldoctor --demo

# Audit a specific folder
skilldoctor ~/path/to/skills

# Machine readable output for scripts and CI
skilldoctor --json
```

No installer fan? The whole tool is one file: download `skilldoctor.py` from this repo and run `python3 skilldoctor.py` the same way. It needs Python 3.10 or newer and nothing else.

## What it checks

| Check | What it catches |
| --- | --- |
| Validity | Frontmatter that does not parse, missing name or description, names that are not kebab-case or do not match their folder, names and descriptions over the spec length limits |
| Security | Downloads piped into a shell, instructions touching credential stores, language that sends user data out, prompt override phrases, uninspectable base64 blobs, destructive commands, invisible Unicode characters, and the same patterns in the text files bundled with a skill |
| Conflicts | The same skill name installed in several host folders, near-duplicate descriptions that make hosts load the wrong skill. Skills namespaced inside a plugin, and the distribution copies inside one collection, are not conflicts |
| Token cost | Always-on tokens (the name and description a host loads into every conversation) counted apart from body tokens, which load only when a skill runs |

## Reading the report

- **OK**: the skill parses, identifies itself properly, and shows no risky patterns.
- **WARN**: worth a human look, for example a reference to a credential store or a very long file.
- **FAIL**: broken or dangerous. The report exits with code 1 when any skill fails, so it drops straight into CI.

## Scores and fixes

Every skill gets a score out of 100 and a letter grade, and so does the whole installation. Errors and high risk findings cost the most, warnings cost a little, and a clean skill sits at 100. Most findings also carry a fix line that says exactly what to change, so the report reads as a work list, not just a verdict.

## Removing what fails

Finding a bad skill is only half the job, so SkillDoctor can clear it out too. Removal is deliberately boring and reversible:

```bash
# Audit, then move every FAIL skill out of its host folder
skilldoctor --quarantine-failed

# The same, with no confirmation prompt, for scripts
skilldoctor --quarantine-failed --yes

# Changed your mind? Put the last batch back
skilldoctor --restore
```

Nothing is deleted outright. Failed skills move to `~/.skilldoctor/quarantine` in a dated batch with a manifest of where each one came from, and `--restore` puts the most recent batch back exactly where it was. Only FAIL verdicts are moved; a WARN is a judgment call, and judgment calls stay yours.

## Show your audit

Publish skills of your own? When your collection passes a SkillDoctor audit, it has earned the badge, and the badge worth wearing is a live one.

Listed projects paste one snippet, once:

```markdown
[![Audited by SkillDoctor](https://dongdarealest.github.io/skilldoctor/badges/<slug>.svg)](https://dongdarealest.github.io/skilldoctor/)
```

The image is served from the registry site, not from your repo, and a scheduled job re-audits every listed repo each day and regenerates it from the latest result. Keep passing and it shows your current score. Stop passing and it flips to a grey recheck plaque until the project passes again. The slug is issued when your registry entry is created. For a place of honor, the same address with `-plaque` before `.svg` gives the large format:

```html
<a href="https://dongdarealest.github.io/skilldoctor/"><img src="https://dongdarealest.github.io/skilldoctor/badges/<slug>-plaque.svg" alt="SkillDoctor audited plaque" width="560"></a>
```

This is a real one, SkillPort's small badge, served live:

[![Audited by SkillDoctor](https://dongdarealest.github.io/skilldoctor/badges/skillport.svg)](https://dongdarealest.github.io/skilldoctor/)

The static route still exists, for announcements and offline use. One command writes a dated snapshot of the badge and the plaque, with the score and month on their faces, plus the machine report, into the audited folder:

```bash
skilldoctor ~/path/to/skills --write-badge
```

A failing audit writes nothing: fix the failures first, then take the badge. A snapshot goes stale the moment the skills change; the live badge cannot, because the daily re-audit speaks for the current state of the repo.

The image alone still proves nothing, and anyone can paste one. The proof is the registry entry: a listing is added only after the maintainers re-run the audit on the public repo and the results match the submitted report, file hashes included. See [REGISTRY.md](REGISTRY.md) for how verification works and how to ask for a listing, and the registry itself at [dongdarealest.github.io/skilldoctor](https://dongdarealest.github.io/skilldoctor/).

## In CI, and as a GitHub Action

This repo doubles as a GitHub Action, so a collection can audit itself on every push:

```yaml
- uses: Dongdarealest/skilldoctor@v0.4.0
```

It fails the build when any skill fails the audit. Anywhere else, the plain command does the same job in CI: `skilldoctor --json` for machines, exit code 1 on any FAIL.

## Why this exists

Public skill collections are growing faster than anyone can review them, and audits of popular collections keep finding files that are invalid, duplicated, or carry instructions no user would accept if they read them. Installing a skill is trusting a stranger's instructions inside your own AI. A checkup should take ten seconds, so here it is.

## Support

SkillDoctor is free and MIT licensed. If it saved you from one bad install, a coffee keeps the next check coming.

<p>
  <a href="https://github.com/sponsors/Dongdarealest"><img src="https://img.shields.io/badge/GitHub%20Sponsors-141414?style=for-the-badge&logo=githubsponsors&logoColor=EA4AAA" alt="Sponsor on GitHub"></a>
  <a href="https://ko-fi.com/dongdarealest"><img src="https://img.shields.io/badge/Ko--fi-141414?style=for-the-badge&logo=kofi&logoColor=FF5E5B" alt="Buy me a coffee on Ko-fi"></a>
</p>

## Contributing

New checks are the most welcome contributions, especially patterns for risks this version does not catch yet. Open an issue with the skill that slipped through, or send a pull request with a test that proves the new check works.

## License

MIT. See [LICENSE](LICENSE).
