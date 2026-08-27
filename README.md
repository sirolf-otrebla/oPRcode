# Disclaimer

Most of this repo has been generated with OpenCode, using Deepseek v4 pro and GPT 5.6 Sol as models. Even though I outlined a very detailed detailed plan, pr-review-description what kind of result I wanted and how to reach it, it is still quite likely to find random AI slop inside it.

# PR Review Skills

OpenCode skills for thorough, plain-language GitHub pull request reviews. The
workflow checks out an immutable PR snapshot, confirms its scope with the user,
runs focused reviewers, validates suspected defects, and injects confirmed
findings into a local Plannotator review session.

The workflow never posts to GitHub, pushes, commits, stages, or modifies the PR
checkout. Plannotator feedback must be returned to the OpenCode session, not
submitted to a GitHub review destination.

The repo is language-agnostic: it reviews any codebase regardless of language.
For this reason it deliberately avoids referring to linters, formatters, or
other language-specific tooling.

Some reviewers execute the changed code to confirm behavior (for example,
bounded stress tests in a disposable worktree). This can be risky: it may spawn
processes that exhaust memory, hang, or cause other unpleasantries depending on
what the code does. Reviewers are instructed to keep runs short and bounded, but
you should still supervise execution. If the agent lacks a tool it needs, it
may decide to install it on its own; guard against this and review any
installation it attempts.

In practice, it is best to run this workflow inside an isolated container
rather than directly on your own host.

## Skills

- `pr-review` is the only user-facing entry point.
- `pr-review-description` explains the PR before detailed review.
- Nine focused review skills cover design, correctness, comments and docstrings,
  side effects, and complexity.
- `pr-review-validator` investigates uncertain candidate findings.
- `pr-review-presenter` deduplicates findings and prepares Plannotator input.

## Requirements

- [OpenCode](https://opencode.ai) with skills enabled.
- `git` — cloning, worktrees, and diff generation.
- `gh` (GitHub CLI) — authenticated, for `gh pr view`.
- `plannotator` — the local review UI, available on `PATH`.
- Python 3 — runs the bundled `write_finding.py` finding helper.
- A POSIX shell (`bash`) — for `scripts/install.sh` and `scripts/validate.sh`.

## Install

Run:

```bash
./scripts/install.sh
```

The installer copies the skill directories to
`~/.config/opencode/skills/`. Restart OpenCode after installation.

Plannotator must also be available on `PATH`. The official minimal verified
installation is:

```bash
curl -fsSL https://plannotator.ai/install.sh | \
  bash -s -- --minimal --verify-attestation
```

## Validate

```bash
./scripts/validate.sh
opencode debug skill
```

Reviewers author findings with the bundled
`skills/pr-review/scripts/write_finding.py` helper, which enforces the finding
schema. Run it with `--help` for usage; it also validates findings and reviewer
directories with `--check` and `--check-dir`.

The artifact contract is documented in
[`docs/contracts/review-artifacts.md`](docs/contracts/review-artifacts.md).
