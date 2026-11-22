---
name: clean-skill
description: Formats meeting notes into a short summary with decisions, owners, and deadlines clearly listed.
---

# Clean Skill

Use this skill when the user pastes raw meeting notes and wants a tidy
summary back.

## Steps

1. Read the notes and pull out every decision that was made.
2. List each action item with the person responsible for it.
3. Note any deadline that was mentioned, exactly as written.
4. Return the summary in three short sections: decisions, actions, dates.

## Rules

- Never invent a decision that is not in the notes.
- If a deadline is ambiguous, quote it instead of guessing.
- Keep the whole summary under 300 words unless the user asks for more.
