---
name: pr-review-logic
description: Use ONLY when delegated by pr-review to find functionally incorrect behavior caused by the frozen PR.
---

# Logic Reviewer

## Tooling Restriction

Use only plain OpenCode tools and, where this workflow directs it, Plannotator.
Do not use Octto or any other agent tool, integration, or UI.

Own only `code-review/logic/`. If the delegation explicitly says the user chose
legacy fallback, use the frozen patch and relevant source under this method.
Otherwise, read the frozen manifest and confirmed scope, then read
`code-review/vademecum/_index.md` first and only the neutral cards
needed for this method. Do not begin with a broad patch, tree, caller, test, or
source scan. If one specific required fact is absent or an exact candidate
snippet or anchor is needed, read only the bounded frozen target. Record its
target and reason in `_status.md`. Never modify source.

For every behavior-affecting change, follow:

- real entry points and direct/indirect callers
- guards, branches, loops, defaults, boundaries, and early returns
- success, empty, malformed, timeout, cancellation, and failure paths
- errors, state transitions, ordering, parsing, serialization, and conversions
- relevant tests and the contracts they actually prove

Compare merge-base and head behavior with the agreed Context, Why, What, How,
and user assumptions. A candidate must name a supported trigger, reachable
caller-to-result path, expected behavior, actual wrong result, impact, and the
changed code that causes it.

Do not report style, missing tests without demonstrated wrong behavior,
hypothetical hardening, invented requirements, or pre-existing defects.

## Procedure And Output

Delegate every candidate to a fresh subagent loading `pr-review-validator`,
supplying relevant card IDs when available and any bounded fallback evidence.
Write a finding only for `confirmed` and `PR_CAUSED: yes`. Merge multiple
symptoms with one root cause.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: logic`, `severity`, `confidence`, `file`, `start_line`, `end_line`,
`side`, and frozen `head_sha`; then title, `Comment`, `Evidence`, `Code`, and
`Suggestion`. Evidence includes the trigger-to-result trace and base/head
comparison. No praise or speculation.

Always write `code-review/logic/_status.md` with exact YAML fields
`reviewer: logic`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`; then state changed behaviors checked and gaps.
