# Validation scenarios

Scenario files describe small deterministic rule cases independently of the Python engine implementation.

The initial JSON shape is intentionally simple:

```json
{
  "name": "...",
  "rule": "...",
  "evidence": ["DOCUMENTED"],
  "preconditions": ["..."],
  "input": {},
  "expected": {}
}
```

A scenario becomes `TESTED` when an automated local test consumes or mirrors it. It becomes `DIFF_VERIFIED` only after the same setup/result has been checked against a NuHost reference run.
