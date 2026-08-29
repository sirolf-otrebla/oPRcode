# Review Artifact Contract

All artifacts live under `<temporary-repository>/code-review/`. Paths and file
names use underscores instead of spaces.

## Frozen Manifest

`_manifest.md` records the immutable review identity:

```yaml
---
pr_url: https://github.com/owner/repository/pull/123
repository: owner/repository
pr_number: 123
title: "Short PR title"
is_draft: false
base_ref: main
base_sha: full_sha
head_ref: feature_branch
head_sha: full_sha
merge_base_sha: full_sha
patch_file: code-review/_changes.patch
---
```

String values use quoted YAML scalars with JSON-compatible escaping. Never
interpolate an untrusted PR title or ref as a bare scalar. Also save the
read-only `gh pr view` response needed by the description agent, including the
title and body, as strict JSON in `_pr_metadata.json`.

The patch is the merge-base-to-head diff captured before delegation. Reviewers
may read unchanged code for context but must not replace this scope with a live
branch or mutable working tree.

## Shared Vademecum

`pr-review-description` performs the one broad technical trace and owns
`code-review/vademecum/` until it is sealed. Every artifact in this directory
is Markdown with headings; JSON, YAML frontmatter, symlinks, and other files are
forbidden.

```text
vademecum/
├── _index.md
├── _inventory.md
├── _seal.md
└── cards/
    └── <kind>-<number>.md
```

The coordinator runs `_vademecum.py prepare` before delegation.
`_inventory.md` records the frozen head and merge-base SHAs, patch hash, and a
stable item ID for every patch hunk or hunkless binary, rename, copy, or mode
change. Each item records structured `Old Path` and `New Path` sections (the
literal `None` marks an absent side, such as a deletion). Every item must be
covered by at least one `CH` card, and a `CH` card may only cover items whose
target path it anchors on the required side: `@new` for existing paths, `@old`
only for deletions. Covering therefore means anchoring and describing that
specific file, so every changed file is named somewhere in the vademecum.

The investigator writes a temporary `_draft.md` using the helper's documented
heading format. A successful `_vademecum.py build` with the frozen patch path
validates the complete draft and inventory against that patch, stages the
complete replacement before swapping directories with rollback on ordinary
failure, writes `_seal.md`, and removes the draft. `_seal.md` records identity,
card inventory, changed-item coverage, and SHA-256 hashes. `_vademecum.py check`
also requires the frozen patch path and reconstructs and verifies the complete
artifact set against it.

`_index.md` is the only mandatory reviewer read. It groups cards by neutral
kind and gives each card's title, first fact, first anchor, and relationships so
a reviewer can load only relevant cards. Per-hunk coverage remains in the seal,
not the mandatory index. The index contains no reviewer routing.

Each card has this shape and no additional sections:

```markdown
# CH-001: Short neutral title

## Kind
`CH`

## Facts
- One supported, non-evaluative fact.
- One base-to-head fact without duplicated background.

## Anchors
- `src/example.py#L10-L14@new`

## Links
- [FL-001](FL-001.md)

## Covers
- `I-0123456789abcdef`
```

Titles are at most 80 characters. A card has one to eight unique facts, each at
most 240 characters. Anchors are repository-relative and use
`path@new|old`, `path#Lstart@new|old`, or `path#Lstart-Lend@new|old`; the
path-only form exists for binary, rename, copy, and mode-only changes with no
meaningful line. Cards link instead of repeating facts and contain no code
snippets, findings, suspected problems, risks, reviewer names, priorities,
severity, praise, recommendations, or threshold information.

Card kinds are factual, not reviewer-specific:

| Kind | Content |
| --- | --- |
| `OV` | PR context, declared intent or labeled inference, observable change, and approach |
| `CH` | One changed file and its base-to-head change; multiple hunks of a file may share a card. Includes a reference fact: inbound importers/callers at head, or that none were found |
| `FL` | Execution or data flow from entry point to observable boundary |
| `CT` | Inputs, outputs, errors, invariants, and compatibility at a boundary |
| `SE` | State ownership, effects, ordering, lifecycle, cleanup, and concurrency |
| `ST` | Responsibilities, collaborators, dependencies, and module boundaries |
| `DP` | Data, configuration, storage, schema, migration, and protocol facts |
| `TS` | Relevant tests, exercised paths, assertions, and factual evidence limits |
| `DC` | Affected comments/docstrings and the durable claims they express |
| `SC` | Input dimensions and base/head work, I/O, memory, or retained-data growth |
| `UN` | One precise unresolved fact, target, bounded search, and related cards |

At least one `OV` and one `CH` card are required. Other kinds are created only
when applicable. There is no global size cap: bounded facts and deduplication
control tokens while complete changed-file coverage takes priority. Because
covering requires anchoring, every changed file appears in `_index.md`, so
reviewers can spot rewrites of files nothing references anymore.

After sealing, all nine reviewers receive the same directory. They read the
index first, select cards independently, and do not start with a broad patch or
repository scan. A reviewer may read one bounded frozen target only for a
specific missing fact, exact candidate text/anchor, or required focused
experiment, and records that fallback in its status body. Relevant card IDs and
fallback evidence accompany any candidate to `pr-review-validator`; the
validator independently verifies decisive facts from the frozen patch and
source.

The presenter does not read the vademecum. User focus, exclusions, operational
assumptions, and severity changes do not alter it. A technical correction or
frozen identity change requires rebuilding it and rerunning reviewers. If build
and one repair attempt both fail, the coordinator asks the user whether to stop
or explicitly use the legacy broad-source workflow.

## Confirmed Scope

`_scope.md` uses this fixed shape:

```markdown
---
confirmed: true
---
## 0. Context
...
## 1. Why
...
## 2. What
...
## 3. How
...
## Additional Context
...
## Focus
...
## Exclusions
...
## Operational Assumptions
...
```

The user sees and confirms the final corrected paragraphs before `confirmed`
becomes true. `_scope.md` never contains the severity threshold.

## Severity Threshold

The chosen presentation threshold is stored separately in `_threshold.md`:

```markdown
---
minimum_severity: medium
---
```

`minimum_severity` is one allowed severity. This file is written by the
orchestrator and read only by the presenter. Reviewers must never see it; the
threshold is presentation-only and reviewers still record all confirmed
severities.

## Reviewer Status

Each reviewer owns `code-review/<reviewer_name>/` and always writes
`_status.md`:

```yaml
---
reviewer: side_effects
result: complete
findings: 1
inconclusive_candidates: 0
---
```

`result` is `complete`, `partial`, or `blocked`. The body briefly states what
was checked and names missing coverage. A clean review is valid only when all
nine reviewer status files are complete.

## Candidate Validation

A suspected issue is not a finding. A dedicated validator returns this envelope
to the requesting reviewer or parent:

```text
VERDICT: confirmed | rejected | inconclusive
CLAIM: one precise claim
EVIDENCE: concrete code path, command, or reproduction
PR_CAUSED: yes | no | unclear
ANCHOR: path:start_line-end_line:new|old
```

Only `confirmed` plus `PR_CAUSED: yes` can become a finding file.

## Finding File

Each confirmed finding is a separate Markdown file named
`<severity>_<path>_<line>_<short_title>.md`. Normalize `/`, `\`, whitespace,
and punctuation in the path and title to underscores so the result is one file
directly inside the reviewer directory.

```markdown
---
id: side_effects_src_pipeline_py_142_unbounded_queue
reviewer: side_effects
severity: high
confidence: 94
file: src/pipeline.py
start_line: 142
end_line: 149
side: new
head_sha: full_sha
---
# Unbounded queue can exhaust memory

## Comment
Concrete user-visible or operational impact.

## Evidence
Reachable reproduction or proof, including independent validation.

## Code
```text
bounded relevant snippet
```

## Suggestion
Smallest practical fix or regression test.
```

Allowed severities, from strongest to weakest:

- `critical`: likely catastrophic security, data-loss, or service-wide failure.
- `high`: serious reachable failure with broad or important impact.
- `medium`: concrete defect with bounded impact or a significant maintenance
  trap likely to cause defects.
- `low`: minor but real defect or localized avoidable maintenance cost.
- `nitpick`: optional small cleanup with a specific readability benefit.

Findings never contain praise, ceremony, unsupported speculation, or unrelated
pre-existing issues.

## Plannotator Batch

The presenter writes `external_annotations.json` using Plannotator's documented
batch API:

```json
{
  "annotations": [
    {
      "source": "pr-review-assistant",
      "scope": "line",
      "type": "concern",
      "filePath": "src/pipeline.py",
      "lineStart": 142,
      "lineEnd": 149,
      "side": "new",
      "text": "[HIGH] Unbounded queue can exhaust memory\n\nImpact...\n\nEvidence...\n\nSuggestion...",
      "author": "Side effects reviewer"
    }
  ]
}
```

Findings below the user's threshold are omitted from this batch. The presenter
also writes `final_review.md` as a session summary whose substance is returned
before temporary cleanup. External annotations are session-scoped and are
injected only into the local Plannotator server.
