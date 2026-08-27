---
name: pr-review-presenter
description: Use ONLY when delegated by pr-review after all reviewers finish to validate, deduplicate, filter, and format confirmed findings for Plannotator.
---

# PR Review Presenter

Finalize artifacts; do not discover findings. Never post to GitHub, launch a
remote PR review, modify source, or promote rejected, inconclusive, malformed,
or non-PR-caused claims.

## Inputs

Require `_manifest.md`, `_scope.md`, `_changes.patch`, and one `_status.md` for
each reviewer: `slap`, `kiss`, `keep_short`, `oop`, `scope`, `logic`,
`documentation`, `side_effects`, and `complexity`.

Validate status fields and reconcile each finding count. A partial or blocked
reviewer is usable but must remain an explicit coverage gap.

Validate every finding:

- unique ID and expected reviewer directory
- allowed severity and confidence from 0 to 100
- repository-relative file, valid line range, and `new` or `old` side
- head SHA exactly matching the frozen manifest
- non-empty Comment, Evidence, Code, and Suggestion sections
- independent confirmation and PR causation stated in its evidence
- anchor includes a changed line represented on that side of `_changes.patch`

Exclude invalid findings rather than guessing repairs.

## Consolidation

Merge findings only when one root cause and one fix explain them. Preserve the
clearest evidence and narrowest valid anchor. Use the strongest justified
severity. Then apply the user's inclusive threshold in this order:

`critical`, `high`, `medium`, `low`, `nitpick`.

Sort retained findings by severity, file, and line. Findings below threshold
appear only as an omitted count.

## Outputs

Write `code-review/final_review.md` with:

- immutable PR identity and head SHA
- the confirmed Context, Why, What, and How
- selected severity threshold
- terse status for all nine reviewers and any missing coverage
- findings first, each with severity, file/line, impact, evidence, and fix
- counts for inspected, merged, invalid, omitted, and presented findings

Do not include greetings, praise, LGTM, approval language, or a scorecard. If no
finding survives, say `No findings met the configured severity threshold.` If
coverage is incomplete, state that immediately beside this sentence.

Write strict JSON to `code-review/external_annotations.json`:

```json
{
  "annotations": [
    {
      "source": "pr-review-assistant",
      "scope": "line",
      "type": "concern",
      "filePath": "src/example.py",
      "lineStart": 10,
      "lineEnd": 12,
      "side": "new",
      "text": "[HIGH] Title\n\nImpact: ...\n\nEvidence: ...\n\nSuggestion: ...",
      "author": "Logic reviewer"
    }
  ]
}
```

Emit one annotation per retained root cause. Use only documented fields. An
empty result is `{ "annotations": [] }`. Ensure JSON parses and its annotation
count equals the presented finding count.

Return the two absolute paths, counts, reviewer status summary, whether the
batch is empty, and: `No GitHub content was posted or modified.`
