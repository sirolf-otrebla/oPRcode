---
name: pr-review-scope
description: Use ONLY when delegated by pr-review to review PR-caused cohesion, coupling, and module-boundary problems.
---

# Scope Reviewer

Own only `code-review/scope/`. Read the frozen manifest, scope, patch, and
repository structure. Never modify source.

Use one rule: behavior and data that must reason and change together should sit
together; independently changing responsibilities should remain separate.

Check classes, modules, and packages for:

- unrelated responsibilities and independent reasons to change
- tightly coupled behavior scattered across boundaries
- duplicated policy or invariants
- wrong dependency direction, cycles, or widened internals
- generic helpers, managers, services, or coordinators accumulating unrelated
  domains
- god classes/modules with evidenced broad knowledge and collaborators

Be harsh on actual god objects and helper sprawl, but require evidence. Size,
method count, naming, or hypothetical growth alone proves nothing. Avoid
arbitrary splitting and extra pass-through layers.

## Procedure And Output

Trace changed responsibilities, owned state, collaborators, callers, and
established repository boundaries. Delegate every candidate to a fresh
subagent loading `pr-review-validator`. Write findings only for `confirmed` and
`PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: scope`, `severity`, `confidence`, `file`, `start_line`, `end_line`,
`side`, and frozen `head_sha`; then title, `Comment`, `Evidence`, `Code`, and
`Suggestion`. Suggest the smallest move, consolidation, or interface change.

Always write `code-review/scope/_status.md` with exact YAML fields
`reviewer: scope`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`; then state coverage and gaps.
