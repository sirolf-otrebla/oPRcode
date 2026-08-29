---
name: pr-review-complexity
description: Use ONLY when delegated by pr-review to investigate PR-caused algorithmic time or memory regressions with research and bounded stress tests.
---

# Complexity Reviewer

## Tooling Restriction

Use only plain OpenCode tools and, where this workflow directs it, Plannotator.
Do not use Octto or any other agent tool, integration, or UI.

Own only `code-review/complexity/`. If the delegation explicitly says the user
chose legacy fallback, use the frozen patch and relevant source under this
method. Otherwise, read the frozen manifest and scope, then read
`code-review/vademecum/_index.md` first and only the neutral cards needed
for this method. Do not begin with a broad patch, tree, caller, test, or source
scan. If one specific required fact is absent, an exact candidate snippet or
anchor is needed, or a focused experiment below requires it, read only the
bounded frozen target. Record its target and reason in `_status.md`. Never
modify PR implementation files. A disposable worktree may contain only a
temporary stress-test harness and generated test data, all removed with the
worktree.

## Relevance Gate

First decide whether the PR changes an algorithm or a path whose work, memory,
I/O, queries, or retained data grows with input size. Relevant examples include
loops, recursion, sorting, joining, scans, batching, pagination, fan-out,
caching, parsing, serialization, graphs, and eager materialization.

If no such change exists, do no web research, create no worktree, run no test,
and write a complete zero-finding status explaining the early exit.

## Analysis

For each relevant path:

1. Define independent input dimensions such as records, existing items, pages,
   graph vertices/edges, retries, concurrency, or bytes.
2. Derive base and head time, auxiliary space, output space, and external-call
   count from the actual call path. State bounds and reachable worst cases.
3. Research material imported operations using official runtime/library docs,
   exact-version source, standards, or maintainer documentation. Record URLs
   and version applicability.
4. Form one precise candidate with changed operation, input dimension, base and
   head behavior, supported trigger, impact, causation, and anchor.

## Mandatory Bounded Test

For every relevant candidate, create a unique detached Git worktree at the
frozen head. Establish cleanup before setup. Use only existing dependencies and
synthetic local data. Do not use credentials, external services, installs, or
production data. Keep each process near 60 seconds or less, avoid host memory
exhaustion, and increase inputs geometrically only until the growth pattern is
clear.

Prefer operation/query counts. When timing or memory matters, use at least
three sizes, keep setup outside measurement, record raw results and limits, and
compare the same harness at frozen base and head. Do not infer precise Big-O
from noisy timing alone.

Always terminate test processes and remove the worktree with
`git worktree remove --force`. Verify its path and worktree-list entry are gone
before writing status. Failed cleanup makes status partial.

## Validation And Output

Delegate every candidate plus relevant card IDs when available, derivation,
sources, bounded fallback evidence, and test evidence to a fresh subagent
loading `pr-review-validator`. Write findings only for `confirmed` and
`PR_CAUSED: yes`.

Author every finding with the bundled `write_finding.py` helper supplied in the
delegation, and verify it with the helper's `--check` mode.

Each finding is one underscore-named Markdown file with YAML fields `id`,
`reviewer: complexity`, `severity`, `confidence`, `file`, `start_line`,
`end_line`, `side`, and frozen `head_sha`; then title, `Comment`, `Evidence`,
`Code`, and `Suggestion`. Evidence includes dimensions, base/head complexity,
sources, exact bounded test, results, and limitations. Severity follows impact,
not Big-O notation.

Always write `code-review/complexity/_status.md` after cleanup with exact YAML
fields `reviewer: complexity`, `result: complete|partial|blocked`, `findings`,
and `inconclusive_candidates`; then state relevance, research/tests performed,
cleanup confirmation, and gaps.
