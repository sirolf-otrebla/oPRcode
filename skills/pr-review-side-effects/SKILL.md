---
name: pr-review-side-effects
description: Use ONLY when delegated by pr-review to find PR-caused side effects, races, ordering failures, and resource lifecycle defects.
---

# Side Effects Reviewer

## Tooling Restriction

Use only plain OpenCode tools and, where this workflow directs it, Plannotator.
Do not use Octto or any other agent tool, integration, or UI.

Own only `code-review/side_effects/`. If the delegation explicitly says the
user chose legacy fallback, use the frozen patch and relevant source under this
method. Otherwise, read the frozen manifest and scope, then read
`code-review/vademecum/_index.md` first and only the neutral cards needed
for this method. Do not begin with a broad patch, tree, caller, test, or source
scan. If one specific required fact is absent or an exact candidate snippet or
anchor is needed, read only the bounded frozen target. Record its target and
reason in `_status.md`. Never invoke production or external systems and never
modify source.

Trace changed paths for:

- mutation, ownership, partial updates, transactions, and rollback
- filesystem, database, network, queue, subprocess, clock, and random I/O
- initialization, shutdown, cancellation, resource acquisition, and cleanup
- shared state, locks, callbacks, tasks, and concrete race interleavings
- retries, idempotency, time budgets, and duplicate effects
- validation/persistence/publication/acknowledgement ordering
- cache keys, invalidation, stale values, and concurrent fills
- external protocol, pagination, delivery, and compatibility assumptions

A candidate needs a concrete trigger, reachable changed path, exact side
effect, failure sequence or interleaving, impact, PR causation, and patch
anchor. `This may race` is not a candidate.

If every hunk is demonstrably incapable of changing side-effect behavior, stop
early and explain that in a complete zero-finding status.

## Procedure And Output

Delegate every candidate to a fresh subagent loading `pr-review-validator`,
supplying relevant card IDs when available and any bounded fallback evidence.
Write findings only for `confirmed` and `PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: side_effects`, `severity`, `confidence`, `file`, `start_line`,
`end_line`, `side`, and frozen `head_sha`; then title, `Comment`, `Evidence`,
`Code`, and `Suggestion`. Evidence gives the trigger-to-impact sequence and
validator result. No praise, hardening wishlist, or speculation.

Always write `code-review/side_effects/_status.md` with exact YAML fields
`reviewer: side_effects`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`; then state dimensions checked, any early-exit reason,
and gaps.
