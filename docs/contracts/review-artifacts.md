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

## Confirmed Scope

`_scope.md` uses this fixed shape:

```markdown
---
confirmed: true
minimum_severity: medium
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
becomes true. `minimum_severity` is one allowed severity.

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
