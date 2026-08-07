"""Move the keep-warm ping into the database itself.

GitHub Actions' free-tier cron proved unreliable as the pinger: a
every-14-minutes schedule actually fired ~20 times a day with multi-hour gaps,
so the Render instance spent most of the day cold anyway, and GitHub's own
runner-acquisition hiccups emailed false alarms. pg_cron fires on time because
it runs inside the always-on Supabase Postgres instance.

The scheduled job asks pg_net to GET /healthz/ every 10 minutes — inside
Render's ~15-minute idle timeout. The handler's database read resets
Supabase's 7-day inactivity timer, closing the loop: Supabase keeps Render
awake, Render keeps Supabase active. No third service involved.

Local dev runs SQLite and skips this entirely (vendor guard below).
"""
from django.db import migrations

HEALTH_URL = "https://songscope.onrender.com/healthz/"

SCHEDULE_SQL = [
    "create extension if not exists pg_cron;",
    "create extension if not exists pg_net;",
    # cron.schedule() upserts by job name, so re-running this migration
    # (or a fresh database) always converges on the same two jobs.
    "select cron.schedule('keep-render-warm', '*/10 * * * *', "
    f"$$select net.http_get('{HEALTH_URL}', timeout_milliseconds := 10000)$$);",
    # cron.job_run_details grows one row per run (~144/day on a 10-minute
    # schedule); trim to a week so the free 500 MB is never an issue.
    "select cron.schedule('purge-cron-history', '10 4 * * 0', "
    "$$delete from cron.job_run_details where end_time < now() - interval '7 days'$$);",
]

UNSCHEDULE_SQL = [
    "select cron.unschedule(jobname) from cron.job "
    "where jobname in ('keep-render-warm', 'purge-cron-history');",
]


def _run(schema_editor, statements):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for sql in statements:
            cursor.execute(sql)


def schedule_keepalive(apps, schema_editor):
    _run(schema_editor, SCHEDULE_SQL)


def unschedule_keepalive(apps, schema_editor):
    _run(schema_editor, UNSCHEDULE_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_alter_spotifytoken_access_token_and_more"),
    ]

    operations = [
        migrations.RunPython(schedule_keepalive, unschedule_keepalive),
    ]
