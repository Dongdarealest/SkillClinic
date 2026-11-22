# The SkillDoctor registry

This registry is the public record of projects that have passed a SkillDoctor audit. A project appears here only after its audit has been verified by the maintainers of this repo.

## The badge is not the proof

Anyone can paste a badge or a plaque image into a README, so the picture alone proves nothing. The proof is the entry on this page. If a project wears the badge but is not listed here, or its listing shows a different score or date, the badge is decoration, not a result.

## How verification works

1. The project runs the audit with the badge flag: `skilldoctor ~/path/to/skills --write-badge`. On a passing audit this writes the badge, the plaque and `skilldoctor-report.json` into the audited folder. The report carries the SHA-256 hash of every audited SKILL.md, the health score, the verdict counts and the audit date.
2. The project asks for a listing and shares the report, or a link to its public repo.
3. The maintainers re-run the audit on the public repo and compare. The verdicts, the health score and the file hashes must match the submitted report. Only then is the entry added below, with the verified date and result.

An entry records the state of a project on its audit date. Changes made after that date are not covered until the project is audited and verified again.

## How to ask for a listing

Open an issue in this repo and attach your `skilldoctor-report.json`, or link your public repo and say where the report lives. Either one works; both together is fastest.

## Verified entries

| Project | Audited | Result |
| --- | --- | --- |
| [SkillPort](https://github.com/Dongdarealest/skillport) | 2026-11-22 | 15 skills across 5 packs, 0 failures. Pack health scores: 100, 100, 100, 100 and 92 |
| [MuseKit](https://github.com/Dongdarealest/musekit) | 2026-11-22 | 6 skills, 0 failures. Health score 100 |

## Freshness

A registry entry is a point in time verification, not a lifetime grade. Each entry is bound to the exact audited files through the SHA-256 hashes in the submitted report. When a listed project changes its audited skills, its printed score describes the earlier state, and the entry counts as stale until the project is re-verified. Every entry shows its verification date so readers can judge freshness for themselves. Re-verification is free: submit a fresh report and the maintainers re-run the audit and update the entry.
