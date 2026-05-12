---
phase: 05-security-hardening
plan: 02
subsystem: frontend-config
tags:
  - security
  - nextjs
  - credential-exposure
  - credential-removal
dependency_graph:
  requires: []
  provides:
    - SEC-02-CLIENT-SECRET-REMOVAL
  affects:
    - frontend/next.config.mjs
    - frontend/package.json
tech_stack:
  added: []
  patterns:
    - Minimal Next.js config (no env block, NEXT_PUBLIC_* vars read from .env.local automatically)
key_files:
  modified:
    - frontend/next.config.mjs
    - frontend/package.json
    - frontend/package-lock.json
  created:
    - frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx
decisions:
  - Remove entire env block from next.config.mjs — NEXT_PUBLIC_BACKEND_URL already in frontend/.env.local, resolved natively by Next.js
  - Remove dotenv from package.json — only consumer was next.config.mjs
  - Commit MetricsStrip.tsx as untracked file was required for build to succeed (deviation Rule 3)
metrics:
  duration: "~7 minutes"
  completed: "2026-05-12T17:22:35Z"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 4
---

# Phase 05 Plan 02: Remove Spotify Credentials from Next.js Frontend Build Pipeline — Summary

## One-liner

Stripped SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID, and REDIRECT_URI from next.config.mjs env block; removed dotenv dependency; verified npm run build exits 0 and bundle contains no credential values.

## What Was Done

Replaced the 23-line `frontend/next.config.mjs` (which loaded the root `.env` via dotenv and baked three Spotify credentials into the browser JS bundle via the `env:` configuration block) with a minimal 4-line file containing only an empty `nextConfig = {}` object and its export.

The `NEXT_PUBLIC_BACKEND_URL` variable is the only frontend-consumed environment variable. It is already defined in `frontend/.env.local` and is resolved by Next.js automatically without any manual `dotenv.config()` call — no functional change from the frontend's perspective.

`dotenv ^16.4.5` was removed from `frontend/package.json` dependencies (it was exclusively used by `next.config.mjs`) and `package-lock.json` was updated accordingly.

A pre-existing blocking issue was resolved: `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` existed in the main repo as an untracked file but was not visible in the git worktree. The build import reference in `profile/page.tsx` caused `npm run build` to fail with "Module not found". The component was committed into the worktree to unblock the build.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Strip credential env block and dotenv from next.config.mjs | ac7b7086 | frontend/next.config.mjs, frontend/package.json, frontend/package-lock.json, frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx |

## Acceptance Criteria Results

| Criterion | Result |
|-----------|--------|
| `grep -c "SPOTIFY_CLIENT_SECRET" frontend/next.config.mjs` = 0 | PASS (0) |
| `grep -c "SPOTIFY_CLIENT_ID" frontend/next.config.mjs` = 0 | PASS (0) |
| `grep -c "REDIRECT_URI" frontend/next.config.mjs` = 0 | PASS (0) |
| `grep -c "dotenv" frontend/next.config.mjs` = 0 | PASS (0) |
| `grep -cE "^\s*env\s*:" frontend/next.config.mjs` = 0 | PASS (0) |
| `grep -c "export default nextConfig" frontend/next.config.mjs` = 1 | PASS (1) |
| `npm run build` exits 0 | PASS |
| Bundle does not contain SPOTIFY_CLIENT_SECRET value | PASS (0 matches in .next/) |
| `grep -c '"dotenv"' frontend/package.json` = 0 | PASS (0) |

## Threat Mitigations

| Threat ID | Category | Status |
|-----------|----------|--------|
| T-05-02 | Information Disclosure — SPOTIFY_CLIENT_SECRET via env block | MITIGATED |
| T-05-06 | Information Disclosure — SPOTIFY_CLIENT_ID via env block | MITIGATED |
| T-05-07 | Tampering — REDIRECT_URI via env block | MITIGATED |
| T-05-08 | DoS — build failure after change | ACCEPTED / NOT TRIGGERED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing MetricsStrip component to enable build**
- **Found during:** Task 1 — build verification
- **Issue:** `frontend/app/profile/page.tsx` imports `./components/MetricsStrip/MetricsStrip` but the file existed only as an untracked file in the main repo working tree — not visible in the git worktree. Build failed with "Module not found".
- **Fix:** Read the component from the main repo's untracked file, created it at the correct path in the worktree, staged and committed it alongside the plan's intended changes.
- **Files modified:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` (created)
- **Commit:** ac7b7086 (same task commit)

## Known Stubs

None — `MetricsStrip.tsx` fetches real data from `/api/recommendation-metrics/`. `NEXT_PUBLIC_BACKEND_URL` is set in `frontend/.env.local`. No stub values remain.

## Threat Flags

None — this plan only removes surface (credential exposure), it does not add new network endpoints, auth paths, or file access patterns.

## Self-Check: PASSED

- `frontend/next.config.mjs` exists: FOUND
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` exists: FOUND
- Commit ac7b7086 exists: FOUND (worktree-agent-a0f9273e5982a96d3)
