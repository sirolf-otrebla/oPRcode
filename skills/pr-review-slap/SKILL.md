---
name: pr-review-slap
description: Use ONLY when delegated by pr-review to find PR-caused Single Level of Abstraction violations.
---

# SLAP Reviewer

Own only `code-review/slap/`. Read the frozen manifest, scope, patch, and enough
unchanged code to understand changed functions. Never modify source.

An abstraction level is the distance from intent:

- High: orchestration and business decisions, explaining what happens.
- Middle: domain operations and rules.
- Low: loops, parsing, storage, protocol, serialization, and language mechanics.

A cohesive function or block should tell one story at one level and delegate
substantial lower-level mechanics to meaningful operations. Report mixing only
when it hides a rule or ordering, couples unrelated changes, obstructs focused
testing, or creates another concrete maintenance risk.

Do not demand one-line wrappers, extraction for line count, or layers that only
move complexity. Small obvious mechanics are harmless when they do not
interrupt the story.

## Procedure And Output

Review every changed function/block. For each candidate, delegate a fresh
subagent that loads `pr-review-validator` and validates one claim. Write a
finding only for `confirmed` and `PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is a separate underscore-named Markdown file with YAML fields:
`id`, `reviewer: slap`, `severity`, `confidence`, `file`, `start_line`,
`end_line`, `side`, and the frozen `head_sha`. Its body contains a title,
`Comment`, `Evidence`, `Code`, and `Suggestion`. Explain the mixed levels,
concrete cost, validator evidence, bounded snippet, and smallest meaningful
boundary to restore. Never include praise or pre-existing issues.

Always write `code-review/slap/_status.md` with exact YAML fields
`reviewer: slap`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`. Briefly state coverage and gaps. No issue is valid.
