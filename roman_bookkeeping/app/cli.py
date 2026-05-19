from flask.cli import with_appcontext
import click

from .db import get_db
from .sync_service import run_full_sync, run_recurring_post


@click.command("nightly-jobs")
@with_appcontext
def nightly_jobs_command():
    """
    Run nightly tasks:
    1) sync invoices/payments
    2) post recurring expenses

    Schedule this from cron/task scheduler in production.
    """
    db = get_db()
    sync_result = run_full_sync(db)
    recurring_result = run_recurring_post(db)

    click.echo(
        "Nightly jobs complete. "
        f"Sync status: {sync_result['status']}, "
        f"rows: {sync_result['rows_processed']}. "
        f"Recurring posted: {recurring_result['rows_processed']}."
    )


def init_app(app):
    app.cli.add_command(nightly_jobs_command)
