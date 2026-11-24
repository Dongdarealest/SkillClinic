# The State of Public Skills

> Note: this report was produced on 22 November 2026, when the tool was still called SkillDoctor. It was renamed to SkillClinic on 24 November 2026; nothing in the audit itself changed.

An audit of the six biggest public skill collections, conducted with SkillClinic on 22 November 2026.

Conducted with SkillClinic (github.com/Dongdarealest/skillclinic), 22 November 2026. Every SKILL.md file was fetched as plain text through the GitHub API and audited for validity, security patterns, conflicts, and token cost. Patterns are heuristic: a FAIL means read this before trusting it, not proof of malice.

Audited 777 skills: 310 OK (40%), 200 WARN (26%), 267 FAIL (34%).

| Collection | Stars | Skills | OK | WARN | FAIL | Health |
| --- | --- | --- | --- | --- | --- | --- |
| anthropics/skills | 198,661 | 20 | 16 | 2 | 2 | 97/100 |
| obra/superpowers | 323,926 | 15 | 15 | 0 | 0 | 100/100 |
| mattpocock/skills | 329,957 | 39 | 37 | 1 | 1 | 99/100 |
| affaan-m/ECC | 308,539 | 500 (first 500) | 92 | 155 | 253 | 76/100 |
| addyosmani/agent-skills | 119,641 | 26 | 16 | 6 | 4 | 92/100 |
| K-Dense-AI/scientific-agent-skills | 58,065 | 177 | 134 | 36 | 7 | 96/100 |

## What the numbers say

The curated collections are nearly clean. Anthropic's own skills score 97, obra/superpowers scores 100, mattpocock/skills scores 99, and K-Dense-AI's scientific collection scores 96. Small, reviewed sets hold up.

The mega collection is where quality goes to die. affaan-m/ECC, the largest set audited, failed 253 of its first 500 skills and carries the audit's lowest health score, 76. Its dominant problems are structural: duplicated skills with identical descriptions competing for the same requests, and files that reference credential stores or mention keys and tokens.

Across all six collections, the most common findings were mentions of API keys, tokens, or passwords (136 skills), references to credential stores (97 skills), and near duplicate descriptions that make hosts load the wrong skill. Eight skills carried the highest severity pattern: instructions to read or send credential material.

## Method and limits

SkillClinic checks four things: frontmatter validity and naming, a set of security patterns matched on the text, conflicts between installed skills, and estimated token cost. It does not execute anything and does not judge whether a skill is good at its job. ECC was capped at its first 500 SKILL.md files. Star counts are as of the audit date. One correction on the token figures quoted when this audit was first published: they were computed from the full text of each SKILL.md, so they measure total text size. Only a skill's name and description are loaded into every conversation; the body loads when the skill is used. SkillClinic 0.3.8 and later report the two costs separately.
