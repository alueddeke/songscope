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
4. Redeploy, then open the Render shell and run:

   ```
   python manage.py migrate
   python manage.py seed_demo
   ```

   `seed_demo` recreates the demo account from
   `DEMO_USER_SPOTIFY_REFRESH_TOKEN`, so a blank database is fully recoverable —
   no dump from the old Render instance is required.
5. Confirm `https://songscope.onrender.com/healthz/` returns
   `{"status": "ok", "database": "ok"}`.

## Staying alive without supervision

Three separate timers would otherwise take the demo down, and
`.github/workflows/keep-warm.yml` resets all three:

| Timer | Trigger | How it is handled |
| --- | --- | --- |
| Render spins the free instance down | ~15 min idle | `/healthz/` pinged every 14 min |
| Supabase pauses the project | 7 days without database activity | `/healthz/` runs a real query, so every ping counts as activity |
| GitHub disables scheduled workflows | 60 days without repository activity | daily job pushes an empty commit to the orphan `keepalive` branch once it is ~50 days stale |

The critical detail is that `/healthz/` performs a database read. The workflow
used to ping `/`, which is the DRF router root and never queries anything — it
kept Render warm while Supabase quietly counted the project as idle.

The ping job fails loudly (non-zero exit) after three attempts so GitHub emails
you instead of silently masking an outage. The `keepalive` branch is an orphan
and is never merged, so `main`'s history stays clean.

## Free-plan headroom

Supabase free allows 500 MB of database storage and 5 GB egress per month;
the demo's usage is a tiny fraction of both. GitHub Actions minutes are
unmetered because this repository is public.
