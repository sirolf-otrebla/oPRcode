# PR Review

## Findings

### [MEDIUM] Missing records still reach the formatter

`src/handler.ts:20` returns a server error for an unknown ID. Return the
established not-found response before formatting.
