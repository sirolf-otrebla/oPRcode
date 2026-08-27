---
name: pr-review-keep-short
description: Use ONLY when delegated by pr-review to find concrete harm from PR-created files or functions that are too long.
---

# Keep Short Reviewer

Own only `code-review/keep_short/`. Read the frozen manifest, scope, patch, and
relevant base/head context. Never modify source.

Use 300 lines per file and 40 lines per function as ideals that prompt
inspection, not limits. Crossing either number is never a finding by itself.
Judge generated code, tables, schemas, fixtures, migrations, and cohesive tests
contextually.

Report only when PR-added length creates a concrete problem:

- unrelated responsibilities must be understood together
- changed policy is entangled with I/O or setup and cannot be tested directly
- one change requires synchronized edits in distant regions
- branches and state interact in a way that obscures correctness

Do not recommend mechanical extraction, one-method wrappers, or splitting a
cohesive scenario merely to meet a number. Distinguish new harm from an already
large unit.

## Procedure And Output

Inventory changed files and logical units, count only to prioritize, then map
responsibilities and test seams. Delegate each candidate to a fresh subagent
loading `pr-review-validator`. Write findings only for `confirmed` and
`PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: keep_short`, `severity`, `confidence`, `file`, `start_line`,
`end_line`, `side`, and frozen `head_sha`; then title, `Comment`, `Evidence`,
`Code`, and `Suggestion`. Suggest the smallest cohesive boundary change.

Always write `code-review/keep_short/_status.md` with exact YAML fields
`reviewer: keep_short`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`; then state coverage and gaps.
