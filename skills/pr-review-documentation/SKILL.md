---
name: pr-review-documentation
description: Use ONLY when delegated by pr-review to check comments and docstrings changed or invalidated by the frozen PR.
---

# Documentation Reviewer

## Tooling Restriction

Use only plain OpenCode tools and, where this workflow directs it, Plannotator.
Do not use Octto or any other agent tool, integration, or UI.

Own only `code-review/documentation/`. If the delegation explicitly says the
user chose legacy fallback, use the frozen patch and relevant source under this
method. Otherwise, read the frozen manifest and scope, then read
`code-review/vademecum/_index.md` first and only the neutral cards needed
for this method. Do not begin with a broad patch, tree, caller, test, or source
scan. If one specific required fact is absent or exact text or an anchor is
needed for a candidate, read only the bounded frozen target. Record its target
and reason in `_status.md`. Never modify source.

Review comments and docstrings, including unchanged ones made inaccurate by the
PR. Useful code documentation explains a durable contract, rationale,
invariant, constraint, hazard, or non-obvious tradeoff. Prefer very brief
comments outside docstrings. Keep docstrings focused on durable caller-facing
contracts when that matches repository conventions.

Check for PR-caused:

- text contradicting implementation, defaults, errors, or supported behavior
- comments that merely narrate obvious code
- redundant text that adds drift risk without useful context
- lines tied to a specific PR, incident, migration step, or temporary situation
  rather than a durable general rule
- explanations better replaced by clearer names, types, constants, or code
- comments or docstrings made materially stale by changed behavior

Historical context is valid only when it explains an ongoing compatibility
rule or invariant. Do not request comments for coverage or ordinary control
flow. Do not broaden this reviewer into a general prose or README review unless
the changed code directly makes that text incorrect.

## Procedure And Output

For every candidate, delegate a fresh subagent loading `pr-review-validator`,
supplying relevant card IDs when available and any bounded fallback evidence.
Write findings only for `confirmed` and `PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: documentation`, `severity`, `confidence`, `file`, `start_line`,
`end_line`, `side`, and frozen `head_sha`; then title, `Comment`, `Evidence`,
`Code`, and `Suggestion`. Prefer deletion or a brief durable correction over
expanded prose. No praise or unrelated cleanup.

Always write `code-review/documentation/_status.md` with exact YAML fields
`reviewer: documentation`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`; then briefly state coverage and gaps.
