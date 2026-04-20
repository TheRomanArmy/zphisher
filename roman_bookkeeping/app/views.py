from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db
from .reports import get_job_profitability_rows, get_profit_and_loss_rows
from .sync_service import run_full_sync, run_invoice_sync, run_payment_sync, run_recurring_post

main_bp = Blueprint("main", __name__)


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@main_bp.route("/")
@login_required
def dashboard():
    db = get_db()
    totals = {
        "invoice_total": db.execute(
            "SELECT COALESCE(SUM(total_amount), 0) AS total FROM imported_invoices"
        ).fetchone()["total"],
        "payment_total": db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM imported_payments"
        ).fetchone()["total"],
        "expense_total": db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses"
        ).fetchone()["total"],
    }

    return render_template("dashboard.html", totals=totals)


@main_bp.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts():
    db = get_db()
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name = request.form.get("name", "").strip()
        account_type = request.form.get("account_type", "").strip()
        category = request.form.get("category", "").strip() or None

        if not code or not name or not account_type:
            flash("Code, name, and account type are required.", "danger")
        else:
            try:
                db.execute(
                    """
                    INSERT INTO accounts (code, name, account_type, category)
                    VALUES (?, ?, ?, ?)
                    """,
                    (code, name, account_type, category),
                )
                db.commit()
                flash("Account added.", "success")
                return redirect(url_for("main.accounts"))
            except Exception as exc:
                flash(f"Could not add account: {exc}", "danger")

    account_rows = db.execute(
        """
        SELECT id, code, name, account_type, category, is_active
        FROM accounts
        ORDER BY code
        """
    ).fetchall()
    return render_template("accounts.html", account_rows=account_rows)


@main_bp.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    db = get_db()
    if request.method == "POST":
        expense_date = request.form.get("expense_date") or date.today().isoformat()
        vendor_name = request.form.get("vendor_name", "").strip()
        description = request.form.get("description", "").strip()
        amount = _as_float(request.form.get("amount"), 0.0)
        account_id = request.form.get("account_id") or None
        job_id = request.form.get("job_id", "").strip() or None
        invoice_id = request.form.get("invoice_id", "").strip() or None

        # If job_id is blank, treat as overhead.
        expense_type = "direct_cost" if job_id else "overhead"

        if amount <= 0:
            flash("Expense amount must be greater than 0.", "danger")
        else:
            db.execute(
                """
                INSERT INTO expenses (
                    expense_date, vendor_name, description, amount,
                    account_id, expense_type, job_id, invoice_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    expense_date,
                    vendor_name,
                    description,
                    amount,
                    account_id,
                    expense_type,
                    job_id,
                    invoice_id,
                ),
            )
            db.commit()
            flash("Expense saved.", "success")
            return redirect(url_for("main.expenses"))

    account_rows = db.execute(
        "SELECT id, code, name FROM accounts WHERE account_type = 'expense' ORDER BY code"
    ).fetchall()
    expense_rows = db.execute(
        """
        SELECT e.id, e.expense_date, e.vendor_name, e.description,
               e.amount, e.expense_type, e.job_id, e.invoice_id,
               a.code AS account_code, a.name AS account_name
        FROM expenses e
        LEFT JOIN accounts a ON a.id = e.account_id
        ORDER BY e.expense_date DESC, e.id DESC
        """
    ).fetchall()
    return render_template(
        "expenses.html", account_rows=account_rows, expense_rows=expense_rows
    )


@main_bp.route("/recurring-expenses", methods=["GET", "POST"])
@login_required
def recurring_expenses():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        vendor_name = request.form.get("vendor_name", "").strip()
        description = request.form.get("description", "").strip()
        amount = _as_float(request.form.get("amount"), 0.0)
        account_id = request.form.get("account_id") or None
        default_job_id = request.form.get("default_job_id", "").strip() or None
        start_date = request.form.get("start_date") or date.today().isoformat()

        expense_type = "direct_cost" if default_job_id else "overhead"

        if not name or amount <= 0:
            flash("Name and valid amount are required.", "danger")
        else:
            db.execute(
                """
                INSERT INTO recurring_expenses (
                    name, vendor_name, description, amount, account_id,
                    expense_type, default_job_id, start_date, next_run_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    vendor_name,
                    description,
                    amount,
                    account_id,
                    expense_type,
                    default_job_id,
                    start_date,
                    start_date,
                ),
            )
            db.commit()
            flash("Recurring expense added.", "success")
            return redirect(url_for("main.recurring_expenses"))

    account_rows = db.execute(
        "SELECT id, code, name FROM accounts WHERE account_type = 'expense' ORDER BY code"
    ).fetchall()
    recurring_rows = db.execute(
        """
        SELECT r.*, a.code AS account_code, a.name AS account_name
        FROM recurring_expenses r
        LEFT JOIN accounts a ON a.id = r.account_id
        ORDER BY r.next_run_date ASC, r.id DESC
        """
    ).fetchall()
    return render_template(
        "recurring_expenses.html",
        account_rows=account_rows,
        recurring_rows=recurring_rows,
    )


@main_bp.post("/recurring-expenses/run-now")
@login_required
def recurring_expenses_run_now():
    result = run_recurring_post(get_db())
    flash(
        f"Recurring posting complete: {result['rows_processed']} expense(s) posted.",
        "success",
    )
    return redirect(url_for("main.recurring_expenses"))


@main_bp.route("/imported-invoices")
@login_required
def imported_invoices():
    db = get_db()
    rows = db.execute(
        """
        SELECT scheduler_invoice_id, customer_id, job_id, invoice_number,
               invoice_date, due_date, total_amount, status, imported_at
        FROM imported_invoices
        ORDER BY invoice_date DESC, id DESC
        """
    ).fetchall()
    return render_template("imported_invoices.html", rows=rows)


@main_bp.route("/imported-payments")
@login_required
def imported_payments():
    db = get_db()
    rows = db.execute(
        """
        SELECT scheduler_payment_id, scheduler_invoice_id, customer_id, job_id,
               payment_date, amount, payment_method, imported_at
        FROM imported_payments
        ORDER BY payment_date DESC, id DESC
        """
    ).fetchall()
    return render_template("imported_payments.html", rows=rows)


@main_bp.route("/reports/profit-loss")
@login_required
def profit_loss_report():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    report = get_profit_and_loss_rows(get_db(), start_date=start_date, end_date=end_date)
    return render_template(
        "report_profit_loss.html",
        report=report,
        start_date=start_date,
        end_date=end_date,
    )


@main_bp.route("/reports/job-profitability")
@login_required
def job_profitability_report():
    rows = get_job_profitability_rows(get_db())
    return render_template("report_job_profitability.html", rows=rows)


@main_bp.route("/settings-sync", methods=["GET", "POST"])
@login_required
def settings_sync():
    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "sync_invoices":
            result = run_invoice_sync(db)
            flash(result["message"], "success" if result["status"] == "success" else "danger")
        elif action == "sync_payments":
            result = run_payment_sync(db)
            flash(result["message"], "success" if result["status"] == "success" else "danger")
        elif action == "sync_full":
            result = run_full_sync(db)
            flash(result["message"], "success" if result["status"] == "success" else "danger")
        return redirect(url_for("main.settings_sync"))

    sync_rows = db.execute(
        """
        SELECT sync_type, started_at, completed_at, status, rows_processed, message
        FROM sync_log
        ORDER BY id DESC
        LIMIT 50
        """
    ).fetchall()

    return render_template("settings_sync.html", sync_rows=sync_rows)
