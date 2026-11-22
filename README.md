# SkillDoctor

**Your AI is running skills you never audited.**

SkillDoctor is a small, zero dependency command line tool that audits the
AI skill files (SKILL.md) already installed on your machine. It checks
every skill it finds for validity, security risks, conflicts, and token
cost, then prints one clear report with a verdict per skill: OK, WARN, or
FAIL.

Skills are powerful. A skill is a set of instructions your AI host loads
and follows, often at the start of every conversation. Most people install
them from repositories, gists, and chat messages without ever reading
them. SkillDoctor reads them for you.

## What it checks

**Validity**
- The YAML frontmatter parses cleanly.
- The required fields, name and description, are present.
- The name is kebab-case and matches the folder the skill lives in.

**Security**
- Shell pipes from the network, such as a download fed straight into bash.
- Instructions that touch credential stores: .env files, ~/.ssh, id_rsa,
  cloud keys, keychains.
- Language that tells the host to send or upload user files and data to an
  external destination.
- Prompt override phrases that tell the host to ignore its instructions.
- Long base64 blobs that no human can inspect at a glance.
- Mentions of API keys, tokens, passwords, and destructive shell commands.

**Conflicts**
- The same skill name installed in more than one host folder, so you never
  know which copy actually loads.
- Near-duplicate descriptions on different skills, which makes hosts load
  the wrong skill for a request.

**Token cost**
- An estimate of the tokens each skill adds, and the total always-on cost
  of everything installed. Bloated skills tax every conversation you have.

## Quick start

You need Python 3.8 or newer. There is nothing to install.

```bash
# Audit the skill folders on this machine
python3 skilldoctor.py

# See it work in ten seconds on the bundled examples
python3 skilldoctor.py --demo

# Audit a specific folder
python3 skilldoctor.py ~/path/to/skills

# Machine readable output for scripts and CI
python3 skilldoctor.py --json
```

By default SkillDoctor scans these locations when they exist:
`~/.claude/skills`, `~/.cursor/skills`, `~/.codex/skills`, and
`~/.config/claude/skills`. Pass one or more paths to scan somewhere else.

The exit code is 1 when any skill earns a FAIL, and 0 otherwise, so it
drops straight into a CI job or a pre-commit check.

SkillDoctor is read only. It never modifies, moves, or deletes the files
it audits.

## Example output

```text
SkillDoctor 0.1.0
Scanned: examples

FAIL  Invalid_Skill Name
      folder: examples/invalid-skill
      tokens: ~67
      - [error] missing required field: description
      - [error] name is not kebab-case: Invalid_Skill Name
      - [error] name 'Invalid_Skill Name' does not match its folder 'invalid-skill'

OK    clean-skill
      folder: examples/clean-skill
      tokens: ~175

FAIL  risky-skill
      folder: examples/risky-skill
      tokens: ~210
      - [high] security: skill pipes a network download straight into a shell
      - [high] security: skill tells the host to ignore its previous instructions
      - [high] security: skill instructs sending user data to an external destination
      - [high] security: skill instructs reading or sending credential material
      - [warn] security: skill references a credential store
      - [warn] security: skill mentions API keys, tokens, or passwords
      - [warn] security: skill contains a long base64 blob that a reader cannot inspect

Summary: 3 skills, 1 OK, 0 WARN, 2 FAIL
Always-on token cost: ~452 tokens loaded into every conversation
```

The three example skills live in the `examples/` folder: one clean, one
invalid, one risky. Run `python3 skilldoctor.py --demo` to audit them.

## Why this exists

Skill collections grow fast, and quality control has not kept up. Audits
of popular skill repositories keep finding the same story: a meaningful
share of published skills are invalid, with broken frontmatter, missing
fields, and names that do not match their folders, and a smaller share
carry genuinely risky instructions, from credential snooping to silent
uploads. Hosts load these files trustingly, and users rarely see them at
all.

SkillDoctor is the ten second check that should happen before a skill is
trusted: is it well formed, is it safe to follow, does it fight with
anything else installed, and what does it cost you on every single
conversation.

## Development

Run the test suite with the standard library only:

```bash
python3 -m unittest discover -s tests -v
```

Contributions are welcome. The bar is simple: zero dependencies, read
only behavior, and a test for every new check.

## Support

SkillDoctor is free and MIT licensed. If it saved you from one bad skill,
you can support the work on [GitHub Sponsors](https://github.com/sponsors/Dongdarealest)
or [Ko-fi](https://ko-fi.com/dongdarealest).

## License

MIT. See [LICENSE](LICENSE).
