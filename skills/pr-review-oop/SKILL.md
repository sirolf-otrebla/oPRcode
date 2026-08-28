---
name: pr-review-oop
description: Use ONLY when delegated by pr-review to review PR-caused object-oriented design defects.
---

# OOP Reviewer

## Tooling Restriction

Use only plain OpenCode tools and, where this workflow directs it, Plannotator.
Do not use Octto or any other agent tool, integration, or UI.

Own only `code-review/oop/`. If the delegation explicitly says the user chose
legacy fallback, use the frozen patch and relevant source under this method.
Otherwise, read the frozen manifest and scope, then read
`code-review/vademecum/_index.md` first and only the neutral cards needed for
this method. Do not begin with a broad patch, tree, caller, test, or source
scan. If one specific required fact is absent or an exact candidate snippet or
anchor is needed, read only the bounded frozen target. Record its target and
reason in `_status.md`. Never modify source. Skip cleanly when OOP is not
meaningful to the change; never demand classes or patterns.

Apply this strict ascending priority:

1. Inheritance is least important. Flag fragile base/subclass coupling,
   incompatible lifecycle, or overrides that bypass required behavior. Prefer
   composition only when it solves an evidenced problem.
2. Polymorphism is more important. Check meaningful substitutability:
   preconditions, results, errors, side effects, ownership, and unsupported
   operations. Nominal interfaces alone provide no value.
3. Encapsulation is most important. Trace state ownership and invariants. Look
   for escaped mutable state, invalid intermediate states, bypassed validation,
   non-atomic related updates, stale derived values, and unclear lifecycle.

## Procedure And Output

Report only a concrete violated contract, reachable invariant failure, or
significant PR-created maintenance trap. Delegate every candidate to a fresh
subagent loading `pr-review-validator`, supplying relevant card IDs when
available and any bounded fallback evidence. Write findings only for
`confirmed` and `PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: oop`, `severity`, `confidence`, `file`, `start_line`, `end_line`,
`side`, and frozen `head_sha`; then title, `Comment`, `Evidence`, `Code`, and
`Suggestion`. Prefer the smallest fix that protects the higher-priority
property. No praise, ceremony, or speculative pattern advice.

Always write `code-review/oop/_status.md` with exact YAML fields
`reviewer: oop`, `result: complete|partial|blocked`, `findings`, and
`inconclusive_candidates`; then state coverage and gaps.
