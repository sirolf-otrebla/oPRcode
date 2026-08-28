---
name: pr-review-description
description: Use ONLY when delegated by pr-review to explain a frozen pull request in four short, plain-language paragraphs before detailed review.
---

# PR Review Description

## Tooling Restriction

Use only plain OpenCode tools and, where this workflow directs it, Plannotator.
Do not use Octto or any other agent tool, integration, or UI.

Perform the review's one broad, neutral investigation. Read the supplied frozen
manifest, patch, PR metadata, prepared `code-review/vademecum/_inventory.md`,
and enough base/head source to explain every change and the machinery it
interacts with. Follow directly relevant callers and callees to entry points,
observable boundaries, state/effect owners, contracts, tests, and affected
documentation. Stop unrelated branches. The patch defines scope; never replace
it with a live diff.

This is explanation and factual mapping, not review. You do not know or predict
what later agents will inspect. Never organize evidence for a reviewer or
include findings, suspected problems, risks, praise, severity, priorities,
recommendations, or "inspect this" guidance. State supported facts. Prefix an
inferred motive with `Inference:` and distinguish PR-declared intent from
observed behavior.

## Vademecum

Own only `code-review/vademecum/` and never modify source or another artifact.
All files in this directory must be Markdown with headings. Read
`python3 code-review/_vademecum.py --help`, then create `_draft.md` in the exact
format documented by the helper. Use stable cards with these neutral kinds:

- `OV`: prior context, declared intent or labeled inference, observable change,
  and implementation approach. At least one is required.
- `CH`: one changed file and its base-to-head change; multiple hunks of one
  file may share a card. A card may only cover inventory items of files it
  anchors and describes, so every changed file needs its own anchored card.
  For each changed code file, include a reference fact: which modules import
  or call it at head, or "no inbound references found at head". If that
  question stays unresolved after a bounded search, record it as a `UN` card
  naming the target and the search attempted.
- `FL`: an execution or data flow from entry point through the changed step to
  an observable boundary or result.
- `CT`: inputs, outputs, errors, invariants, and compatibility at a contract or
  API boundary.
- `SE`: state ownership, mutation or external effects, ordering, lifecycle,
  cleanup, and concurrency facts.
- `ST`: module/package responsibilities, collaborators, dependency direction,
  and established boundaries.
- `DP`: schemas, configuration, storage, wire formats, defaults, migrations,
  producers, and consumers.
- `TS`: relevant tests, exercised paths, assertions actually proved, and
  factual limits of that evidence.
- `DC`: affected comments or docstrings, the durable claim or rationale they
  express, and their relationship to behavior.
- `SC`: independent input dimensions, operations, I/O, retained data, and
  known base/head growth characteristics.
- `UN`: one precise unresolved fact, its exact target, the bounded search
  attempted, and related card IDs.

Create only applicable cards. Keep each fact unique, concrete, and short; link
instead of repeating it. Use no code snippets. Prefer symbols and
repository-relative `path@new|old`, `path#Lstart-Lend@new`, or
`path#Lstart-Lend@old` anchors; use the `path@new|old` form only when no line
anchor is meaningful (binary, rename, mode-only). A card has at most eight
facts and each fact at most 240 characters. Its title is at most 80 characters.
Do not create empty cards merely to represent a kind.

Run:

```text
python3 code-review/_vademecum.py build --dir code-review/vademecum \
  --patch code-review/_changes.patch
python3 code-review/_vademecum.py check --dir code-review/vademecum \
  --patch code-review/_changes.patch
```

Do not return until both commands succeed. The generated `_index.md` must let a
reader identify relevant cards without opening all of them.

## Description Output

After sealing the vademecum, return exactly four paragraphs and nothing else,
in this order:

```text
0. Context: <where this change fits and the relevant prior behavior>

1. Why: <the problem or goal>

2. What: <the observable changes>

3. How: <the implementation approach>
```

Each complete paragraph, including its label, must be at most 300 characters.
Check the character counts before returning.
