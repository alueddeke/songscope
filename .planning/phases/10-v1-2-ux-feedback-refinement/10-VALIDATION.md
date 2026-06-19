---
phase: 10
slug: v1-2-ux-feedback-refinement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest / React Testing Library |
| **Config file** | `jest.config.js` |
| **Quick run command** | `npm test -- --testPathPattern=src/components` |
| **Full suite command** | `npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm test -- --testPathPattern=src/components`
- **After every plan wave:** Run `npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | SYNC-01 | — | N/A | unit | `npm test -- --testPathPattern=FeedbackButtonGroup` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | SYNC-02 | — | N/A | unit | `npm test -- --testPathPattern=FeedbackButtonGroup` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | SYNC-03 | — | N/A | unit | `npm test -- --testPathPattern=FeedbackButtonGroup` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | EVOLVE-01 | — | N/A | unit | `npm test -- --testPathPattern=ImprovementStory` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | EVOLVE-02 | — | N/A | unit | `npm test -- --testPathPattern=MetricsStrip` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | UI-01 | — | N/A | unit | `npm test -- --testPathPattern=TopArtists` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | UI-02 | — | N/A | unit | `npm test -- --testPathPattern=TopArtists` | ❌ W0 | ⬜ pending |
| 10-03-03 | 03 | 2 | UI-03 | — | N/A | unit | `npm test -- --testPathPattern=TopArtists` | ❌ W0 | ⬜ pending |
| 10-03-04 | 03 | 2 | UI-04 | — | N/A | visual | Manual: inspect profile page in browser | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/components/__tests__/FeedbackButtonGroup.test.tsx` — stubs for SYNC-01, SYNC-02, SYNC-03
- [ ] `src/components/__tests__/ImprovementStory.test.tsx` — stubs for EVOLVE-01
- [ ] `src/components/__tests__/MetricsStrip.test.tsx` — stubs for EVOLVE-02
- [ ] `src/components/__tests__/TopArtists.test.tsx` — stubs for UI-01, UI-02, UI-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Profile page visual regression check | UI-04 | CSS class change (bg-gray-800) requires visual inspection | Open profile page in browser, expand TopArtists section, confirm expanded area has visible dark background |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
