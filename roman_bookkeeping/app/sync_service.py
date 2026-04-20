import sqlite3
from datetime import date, datetime, timedelta

from flask import current_app


SYNC_SQL = """
INSERT INTO sync_log (sync_type, started_at, completed_at, status, rows_processed, message)
VALUES (?, ?, ?, ?, ?, ?)
"""


def _connect_scheduler_db():
    return sqlite3.connect(current_app.config["SCHEDULER_DB"])


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table_name,)
    ).fetchone()
    return row is not None


def _log_sync(db, sync_type, status, rows_processed, message, started_at=None):
    started_at = started_at or datetime.utcnow().isoformat(timespec="seconds")
    completed_at = datetime.utcnow().isoformat(timespec="seconds")
    db.execute(
        SYNC_SQL,
        (sync_type, started_at, completed_at, status, rows_processed, message),
    )
    db.commit()


def run_invoice_sync(db):
    started_at = datetime.utcnow().isoformat(timespec="seconds")
    inserted = 0

    try:
        scheduler = _connect_scheduler_db()
        if not _table_exists(scheduler, "invoices"):
            message = "Scheduler DB missing expected table: invoices"
            _log_sync(db, "invoices", "failed", 0, message, started_at)
            return {"status": "failed", "rows_processed": 0, "message": message}

        # Expected scheduler columns (v1 assumption):
        # id, customer_id, job_id, invoice_number, invoice_date, due_date,
        # subtotal, tax_amount, total_amount, status, updated_at
        rows = scheduler.execute(
            """
            SELECT id, customer_id, job_id, invoice_number,
                   invoice_date, due_date, subtotal, tax_amount,
                   total_amount, status, updated_at
            FROM invoices
            """
        ).fetchall()

        for row in rows:
            db.execute(
                """
                INSERT INTO imported_invoices (
                    scheduler_invoice_id, customer_id, job_id, invoice_number,
                    invoice_date, due_date, subtotal, tax_amount,
                    total_amount, status, source_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scheduler_invoice_id) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    job_id = excluded.job_id,
                    invoice_number = excluded.invoice_number,
                    invoice_date = excluded.invoice_date,
                    due_date = excluded.due_date,
                    subtotal = excluded.subtotal,
                    tax_amount = excluded.tax_amount,
                    total_amount = excluded.total_amount,
                    status = excluded.status,
                    source_updated_at = excluded.source_updated_at,
                    imported_at = CURRENT_TIMESTAMP
                """,
                row,
            )
            inserted += 1

        db.commit()
        scheduler.close()

        message = f"Invoice sync completed ({inserted} rows processed)."
        _log_sync(db, "invoices", "success", inserted, message, started_at)
        return {"status": "success", "rows_processed": inserted, "message": message}
    except Exception as exc:
        message = f"Invoice sync failed: {exc}"
        _log_sync(db, "invoices", "failed", inserted, message, started_at)
        return {"status": "failed", "rows_processed": inserted, "message": message}


def run_payment_sync(db):
    started_at = datetime.utcnow().isoformat(timespec="seconds")
    inserted = 0

    try:
        scheduler = _connect_scheduler_db()
        if not _table_exists(scheduler, "payments"):
            message = "Scheduler DB missing expected table: payments"
            _log_sync(db, "payments", "failed", 0, message, started_at)
            return {"status": "failed", "rows_processed": 0, "message": message}

        # Expected scheduler columns (v1 assumption):
        # id, invoice_id, customer_id, job_id, payment_date,
        # amount, method, reference_no, updated_at
        rows = scheduler.execute(
            """
            SELECT id, invoice_id, customer_id, job_id,
                   payment_date, amount, method, reference_no, updated_at
            FROM payments
            """
        ).fetchall()

        for row in rows:
            db.execute(
                """
                INSERT INTO imported_payments (
                    scheduler_payment_id, scheduler_invoice_id,
                    customer_id, job_id, payment_date,
                    amount, payment_method, reference_no,
                    source_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scheduler_payment_id) DO UPDATE SET
                    scheduler_invoice_id = excluded.scheduler_invoice_id,
                    customer_id = excluded.customer_id,
                    job_id = excluded.job_id,
                    payment_date = excluded.payment_date,
                    amount = excluded.amount,
                    payment_method = excluded.payment_method,
                    reference_no = excluded.reference_no,
                    source_updated_at = excluded.source_updated_at,
                    imported_at = CURRENT_TIMESTAMP
                """,
                row,
            )
            inserted += 1

        db.commit()
        scheduler.close()

        message = f"Payment sync completed ({inserted} rows processed)."
        _log_sync(db, "payments", "success", inserted, message, started_at)
        return {"status": "success", "rows_processed": inserted, "message": message}
    except Exception as exc:
        message = f"Payment sync failed: {exc}"
        _log_sync(db, "payments", "failed", inserted, message, started_at)
        return {"status": "failed", "rows_processed": inserted, "message": message}


def run_recurring_post(db):
    started_at = datetime.utcnow().isoformat(timespec="seconds")
    posted = 0

    today = date.today().isoformat()
    rows = db.execute(
        """
        SELECT id, name, vendor_name, description, amount,
               account_id, expense_type, default_job_id,
               interval_unit, interval_value, next_run_date
        FROM recurring_expenses
        WHERE is_active = 1
          AND next_run_date <= ?
        ORDER BY next_run_date ASC
        """,
        (today,),
    ).fetchall()

    for row in rows:
        db.execute(
            """
            INSERT INTO expenses (
                expense_date, vendor_name, description, amount,
                account_id, expense_type, job_id, recurring_expense_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                today,
                row["vendor_name"] or row["name"],
                row["description"] or f"Auto-posted recurring expense: {row['name']}",
                row["amount"],
                row["account_id"],
                row["expense_type"],
                row["default_job_id"],
                row["id"],
            ),
        )

        current = datetime.strptime(row["next_run_date"], "%Y-%m-%d").date()
        if row["interval_unit"] == "weekly":
            next_date = current + timedelta(days=7 * int(row["interval_value"]))
        elif row["interval_unit"] == "yearly":
            next_date = current + timedelta(days=365 * int(row["interval_value"]))
        else:
            # TODO: replace with true month math if your business needs exact calendar month handling.
            next_date = current + timedelta(days=30 * int(row["interval_value"]))

        db.execute(
            "UPDATE recurring_expenses SET next_run_date = ? WHERE id = ?",
            (next_date.isoformat(), row["id"]),
        )
        posted += 1

    db.commit()

    message = f"Recurring auto-post completed ({posted} expense entries posted)."
    _log_sync(db, "recurring_post", "success", posted, message, started_at)
    return {"status": "success", "rows_processed": posted, "message": message}


def run_full_sync(db):
    invoice_result = run_invoice_sync(db)
    payment_result = run_payment_sync(db)

    total = invoice_result["rows_processed"] + payment_result["rows_processed"]
    status = (
        "success"
        if invoice_result["status"] == "success" and payment_result["status"] == "success"
        else "failed"
    )
    message = (
        f"Full sync done. Invoices: {invoice_result['rows_processed']}, "
        f"Payments: {payment_result['rows_processed']}."
    )

    _log_sync(db, "full", status, total, message)
    return {"status": status, "rows_processed": total, "message": message}
