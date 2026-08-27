---
id: logic_src_handler_ts_20_missing_result
reviewer: logic
severity: medium
confidence: 96
file: src/handler.ts
start_line: 20
end_line: 20
side: new
head_sha: 1111111111111111111111111111111111111111
---
# Missing records still reach the formatter

## Comment
An unknown ID reaches the formatter as undefined and returns a server error.

## Evidence
Validator confirmed the public handler reaches this line and the base branch
returned a not-found response.

## Code
```text
return format(record)
```

## Suggestion
Return the established not-found response before calling the formatter.
