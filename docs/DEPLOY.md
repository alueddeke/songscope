# Deploying SongScope (free tier, unattended)

The public demo runs entirely on free plans: the Django API on Render, Postgres
on Supabase, and a GitHub Actions cron holding both awake. This document is the
runbook for that setup and the reasoning behind the non-obvious parts.

## Why the database moved off Render

Render's free Postgres instances expire after 30 days and are then deleted.
When ours expired the web service could no longer open a connection, Django
raised `OperationalError` during boot, and the instance exited with status 1 in
a loop. Supabase's free Postgres does not expire, so it can host the demo
indefinitely — but it pauses on inactivity, which the cron below handles.

## Connection string (the part that is easy to get wrong)

Supabase offers three connection endpoints. Only one of them works here:

| Endpoint | Address | Verdict |
| --- | --- | --- |
| Direct | `db.<ref>.supabase.co:5432` | ❌ IPv6-only without the paid IPv4 add-on; Render cannot reach it |
| Transaction pooler | `aws-<region>.pooler.supabase.com:6543` | ❌ multiplexes connections; breaks persistent connections and server-side cursors |
| **Session pooler** | `aws-<region>.pooler.supabase.com:5432` | ✅ full Postgres over IPv4, safe for Django |

So `DATABASE_URL` must be:

```
postgres://postgres.<project-ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres
```

`backend/config/settings.py` parses this with `dj-database-url` and requires SSL
whenever `DEBUG` is off. As a safety net it detects a `:6543/` URL and degrades
to `CONN_MAX_AGE=0` + `DISABLE_SERVER_SIDE_CURSORS=True`, so pasting the wrong
string yields a slower app rather than cryptic runtime failures.

## First-time setup

1. Create a free Supabase project in a region near the Render service.
2. Copy the **Session pooler** URI from *Project Settings → Database*.
3. In the Render dashboard, set `DATABASE_URL` to that URI.
4. Redeploy. Nothing manual after that: the start command runs `seed_demo`,
   which applies migrations first and then recreates the demo account from
   `DEMO_USER_SPOTIFY_REFRESH_TOKEN` — a blank database is fully recoverable,
   no dump from the old instance required. Migration `0010_keepalive_pg_cron`
   also re-schedules the keep-warm jobs (below) on the fresh database.
5. Confirm `https://songscope.onrender.com/healthz/` returns
   `{"status": "ok", "database": "ok", "keepalive_jobs": 2}`.

## Staying alive without supervision

Three separate timers would otherwise take the demo down:

| Timer | Trigger | How it is handled |
| --- | --- | --- |
| Render spins the free instance down | ~15 min idle | Supabase `pg_cron` GETs `/healthz/` every 10 min via `pg_net` |
| Supabase pauses the project | 7 days without database activity | `/healthz/` runs a real query, so every ping counts as activity |
| GitHub disables scheduled workflows | 60 days without repository activity | daily job pushes an empty commit to the orphan `keepalive` branch once it is ~50 days stale |

The ping lives in the database itself (migration `0010_keepalive_pg_cron`),
not in GitHub Actions: GitHub's free-tier cron delivered only ~20 of ~100
scheduled runs a day with multi-hour gaps, so Render slept between pings, and
runner hiccups emailed false alarms. pg_cron fires on time because it runs
inside the always-on Postgres instance, and its ping loop is self-reinforcing:
Supabase keeps Render awake, Render's `/healthz/` read keeps Supabase active.
A weekly `purge-cron-history` job trims `cron.job_run_details`.

`.github/workflows/keep-warm.yml` is now a daily watchdog. It requires a 200
from `/healthz/` **and** `"keepalive_jobs": 2` in the body (the handler counts
the pg_cron jobs), failing loudly so GitHub emails you if the deploy breaks,
the database is wiped, or the cron schedule disappears. The `keepalive` branch
is an orphan and is never merged, so `main`'s history stays clean.

## Free-plan headroom

Supabase free allows 500 MB of database storage and 5 GB egress per month;
the demo's usage is a tiny fraction of both. GitHub Actions minutes are
unmetered because this repository is public.
