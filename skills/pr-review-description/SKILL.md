---
name: pr-review-description
description: Use ONLY when delegated by pr-review to explain a frozen pull request in four short, plain-language paragraphs before detailed review.
---

# PR Review Description

Read the supplied manifest, frozen patch, PR metadata, and enough unchanged
code to understand the changed path. The patch defines scope. Do not replace it
with a live diff.

Explain rather than review. Do not include findings, risks, praise, severity,
recommendations, implementation trivia, or unrelated context. Prefer ordinary
words. State supported facts; prefix an inferred motive with `Inference:`.

Return exactly four paragraphs and nothing else, in this order:

```text
0. Context: <where this change fits and the relevant prior behavior>

1. Why: <the problem or goal>

2. What: <the observable changes>

3. How: <the implementation approach>
```

Each complete paragraph, including its label, must be at most 300 characters.
Check the character counts before returning.
