---
status: partial
phase: 08-frontend-score-breakdown
source: [08-VERIFICATION.md]
started: 2026-05-19T15:40:00Z
updated: 2026-05-19T15:40:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Score bars render on gem card with data
expected: Gem card with populated score_breakdown shows exactly 3 labeled rows ("Genre Match", "Novelty", "Feedback") with filled green bars and nearest-5% percentage labels

result: [pending]

### 2. Empty score_breakdown shows no bar section
expected: Gem card where score_breakdown is {} or absent renders no bar section at all — no placeholder, no greyed rows, no labels

result: [pending]

### 3. Hit rate tile replaces Acceptance rate
expected: MetricsStrip shows a "Hit rate" tile with an integer-percentage value; no "Acceptance rate" label appears anywhere on the page

result: [pending]

### 4. Hit rate null fallback
expected: When compound_hit_rate is null or missing, MetricsStrip Hit rate tile displays "—" (em dash fallback)

result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
