# The SkillDoctor registry

This registry is the public record of projects that have passed a SkillDoctor audit. It lives at [dongdarealest.github.io/skilldoctor](https://dongdarealest.github.io/skilldoctor/), and most projects in it got there by themselves: they wore the badge, and the registry found them.

## The badge is not the proof

Anyone can paste a badge or a plaque image into a README, so the picture alone proves nothing. The proof is the entry in this registry. If a project wears the badge but is not listed here, or its listing shows a different score or date, the badge is decoration, not a result.

## Wear the badge, get listed

Enrollment is one paste. Your badge address carries your own GitHub identity, and nobody issues it to you:

```
https://skilldoctor-badges.vercel.app/badges/<owner>--<repo>.svg
```

Build it from your owner and repo names, or use the generator at the top of the [registry page](https://dongdarealest.github.io/skilldoctor/), which builds the ready to paste badge and plaque snippets from a repo name. Paste the snippet into your README. That is the whole enrollment; there is no submission step.

A scheduled workflow (`.github/workflows/registry-verify.yml`, running `tools/registry_build.py`) then does the rest, every day:

1. It searches GitHub code search for the badge address and reads the owner and repo out of every address it finds. Repos not yet listed are enrolled on the spot.
2. It audits every listed repo from a fresh clone. Discovered repos are audited at their root, where the tool finds skills recursively; projects listed by hand can name a folder instead.
3. It regenerates each project's badge and plaque from the latest result and republishes this registry.

One scoring rule applies to everyone: the score on the plaque is the health score the audit reports for the project's audit path, nothing else. Sample data never enters that score: skills found under `examples/`, `fixtures/` or `testdata/` folders are exhibits, not installations, so the audit lists them as not audited and excludes them from scoring, verdicts and conflict checks. A project whose only skills are sample data has no score at all, and the registry says so instead of inventing one.

One honest delay, and no broken images. The badge address answers from the moment it is pasted, showing a pending design until the first verification, so a README never renders a missing image. The score itself arrives at the next daily verification run, and GitHub code search indexing can delay discovery of a brand new badge by some hours. A badge pasted today normally shows its true score tomorrow.

## States, and leaving

- **Pending**: the badge is pasted but the repo has not been audited yet. The address shows the pending design, with no score.
- **Current**: the latest daily audit passes. The images show the current score, the skill count and the verification month.
- **No skills**: the project carries no auditable skills at all, because everything the audit found is sample data or because the repo simply has no skills in it. The images keep the standard gold design but read "No skills to audit", with no score: wearing the badge is not itself a result. SkillDoctor's own repo sits in this state, since it ships demo fixtures and no skills of its own.
- **Recheck needed**: the latest daily audit fails, or the repo cannot be cloned or audited. The images flip to a grey recheck design with no score, and the registry entry says why. An old score is never silently kept: a project that stops passing stops showing it, and flips back the day it passes again.
- **Dropped**: take the badge address out of your README and the next run removes the entry and its generated images. Projects listed by hand are removed the same way by the maintainers, on request.

The workflow searches with the token the maintainers give it. A dedicated search token can be supplied as the `REGISTRY_SEARCH_TOKEN` repository secret; without one, the workflow's own token is used.

## Listing by hand

A project that wants a human check first, or a listing at a chosen folder instead of the repo root, can still ask:

1. Run the audit with the badge flag: `skilldoctor ~/path/to/skills --write-badge`. On a passing audit this writes the badge, the plaque and `skilldoctor-report.json` into the audited folder. The report carries the SHA-256 hash of every audited SKILL.md, the health score, the verdict counts and the audit date.
2. Open an issue in this repo and attach the report, or link your public repo and say where the report lives.
3. The maintainers re-run the audit on the public repo and compare. The verdicts, the health score and the file hashes must match the submitted report. Only then is the project added to `registry/projects.json` by hand.

The static files that `--write-badge` writes remain useful as a dated snapshot, for a launch announcement or offline use. They go stale when the skills change; the live badge cannot, because it speaks for the state of the repo at the last daily check, and says so.

## The plain mark

The mark at `https://skilldoctor-badges.vercel.app/badges/audited.svg` is the plain SkillDoctor symbol. It carries no score, names no repo, and enrolls nothing. Only a personal address is an enrollment.

## Verified entries

The living record, with current scores and states, is the registry site. The first entries, enrolled by hand on the date shown, were:

| Project | Audited | Result |
| --- | --- | --- |
| [SkillPort](https://github.com/Dongdarealest/skillport) | 2026-11-22 | Audited at its packs folder: 30 skills, 0 failures. Health score 98 |
| [MuseKit](https://github.com/Dongdarealest/musekit) | 2026-11-22 | Audited at its starter-skills folder: 6 skills, 0 failures. Health score 100 |
| [SkillDoctor](https://github.com/Dongdarealest/skilldoctor) | 2026-11-22 | Audited at its root: no skills of its own, only the demo fixtures under `examples/`, listed as not audited. State: No skills, no score |
