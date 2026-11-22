# The SkillDoctor registry

This registry is the public record of projects that have passed a SkillDoctor audit. It lives at [dongdarealest.github.io/skilldoctor](https://dongdarealest.github.io/skilldoctor/), and a project appears in it only after its audit has been verified by the maintainers of this repo.

## The badge is not the proof

Anyone can paste a badge or a plaque image into a README, so the picture alone proves nothing. The proof is the entry in this registry. If a project wears the badge but is not listed here, or its listing shows a different score or date, the badge is decoration, not a result.

## How verification works

1. The project runs the audit with the badge flag: `skilldoctor ~/path/to/skills --write-badge`. On a passing audit this writes the badge, the plaque and `skilldoctor-report.json` into the audited folder. The report carries the SHA-256 hash of every audited SKILL.md, the health score, the verdict counts and the audit date.
2. The project asks for a listing and shares the report, or a link to its public repo.
3. The maintainers re-run the audit on the public repo and compare. The verdicts, the health score and the file hashes must match the submitted report. Only then is the project added to `registry/projects.json`, with a slug of its own.

## The live badge

A listing is not a snapshot. Once a project is listed, its badge and plaque are served from the registry site:

- `https://dongdarealest.github.io/skilldoctor/badges/<slug>.svg`
- `https://dongdarealest.github.io/skilldoctor/badges/<slug>-plaque.svg`

The wearer pastes one snippet once, and the images update themselves. A scheduled workflow (`.github/workflows/registry-verify.yml`, running `tools/registry_build.py`) re-audits every listed repo from a fresh clone each day, regenerates the images from the latest result, and republishes this registry. The freshness rule is enforced by the system itself, not by anyone remembering to check:

- **Current**: the latest daily audit passes. The images show the current score, the skill count and the verification month. A collection is scored by its weakest group, so one slipping pack lowers the whole plaque.
- **Recheck needed**: the latest daily audit fails, or the repo cannot be cloned or audited. The images flip to a grey recheck design with no score, and the registry entry says why. The old score is never silently kept: a project that stops passing stops showing it, and flips back the day it passes again.

The static files that `--write-badge` writes remain useful as a dated snapshot, for a launch announcement or offline use. They go stale when the skills change; the live badge cannot, because it speaks for the state of the repo at the last daily check, and says so.

## How to ask for a listing

Open an issue in this repo and attach your `skilldoctor-report.json`, or link your public repo and say where the report lives. Either one works; both together is fastest.

## Verified entries

The living record, with current scores and states, is the registry site. The first entries, verified by hand on the date shown, were:

| Project | Audited | Result |
| --- | --- | --- |
| [SkillPort](https://github.com/Dongdarealest/skillport) | 2026-11-22 | 15 skills across 5 packs, 0 failures. Pack health scores: 100, 100, 100, 100 and 92 |
| [MuseKit](https://github.com/Dongdarealest/musekit) | 2026-11-22 | 6 skills, 0 failures. Health score 100 |
