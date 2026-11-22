# SkillDoctor audit of the large public skill collections: draft, scan pending

Status: research inventory complete, auditor runs not yet performed. The shallow clones of the three named repositories completed, but the clone step was flagged by an automated execution risk check, and the cloned content has not been copied, scanned, or otherwise processed pending an explicit go ahead. No numbers in this draft come from the auditor yet, and none should be quoted until the scan runs.

## Collections identified

Named in the brief, all public, all cloned shallowly into a scratch folder:

| Repository | Stars at research time | Notes |
| --- | --- | --- |
| mattpocock/skills | about 330,000 | Skills for engineers, from the author's own agent setup |
| obra/superpowers | about 324,000 | Agentic skills framework and development methodology |
| anthropics/skills | about 199,000 | The official public Agent Skills repository |

Additional large collections found through GitHub search, all above 5,000 stars, candidates for the same audit:

| Repository | Stars at research time | Notes |
| --- | --- | --- |
| affaan-m/ECC | about 309,000 | Agent harness system with skills and instincts |
| addyosmani/agent-skills | about 120,000 | Production engineering skills for coding agents |
| K-Dense-AI/scientific-agent-skills | about 58,000 | Scientific agent skills library |
| sickn33/agentic-awesome-skills | about 50,000 | Large reusable agent skills collection |
| wshobson/agents | about 43,000 | Plugins, agents, skills, and commands for several hosts |

Star counts are from the GitHub search API on 2026-11-22 and will drift.

## Planned method

For each repository: collect every SKILL.md, group the skill folders into one scan root per repository, run SkillDoctor in JSON mode against that root, and record total skills, OK, WARN, and FAIL counts, the most common validity errors, the most common security pattern hits, the total always-on token cost, and the single most serious concrete finding with its file path.

## Methods note

SkillDoctor's checks are heuristic pattern matching, not proof. A FAIL verdict means "read this file carefully before trusting it", not that a skill is malicious. Many flagged patterns have legitimate uses in the right context, and this report will say so wherever the numbers are presented.

## Headline findings

Pending the scan. Three candidate headlines will be written from the real counts once the auditor has run, stated conservatively and without naming any author as careless or malicious.
