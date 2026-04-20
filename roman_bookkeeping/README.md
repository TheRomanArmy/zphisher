# roman_bookkeeping

A separate Flask + SQLite bookkeeping app that integrates with your scheduler/invoice software while keeping bookkeeping data in its own database.

## What Version 1 includes

- Login page
- Dashboard
- Chart of Accounts page
- Expenses page (auto-overhead if no `job_id`)
- Recurring Expenses page (with manual `Run Auto-Post Now`)
- Imported Invoices page
- Imported Payments page
- Profit & Loss report page
- Job Profitability report page
- Settings / Sync page

## Separation of databases

- Bookkeeping DB: `instance/bookkeeping.sqlite3`
- Scheduler DB path: `instance/scheduler.sqlite3` (or set `SCHEDULER_DB_PATH` env var)

No scheduler data is edited by this app. It reads scheduler tables and upserts into bookkeeping import tables.

## Expected scheduler tables in v1

- `invoices` with columns:
  - `id, customer_id, job_id, invoice_number, invoice_date, due_date, subtotal, tax_amount, total_amount, status, updated_at`
- `payments` with columns:
  - `id, invoice_id, customer_id, job_id, payment_date, amount, method, reference_no, updated_at`

If your existing scheduler schema differs, adjust `app/sync_service.py` mappings.

## Quick start

1) Create virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Initialize bookkeeping DB:

```bash
flask --app run.py init-db
```

3) Run app:

```bash
flask --app run.py run
```

4) Login:

- URL: `http://127.0.0.1:5000/login`
- Username: `admin`
- Password: `admin123`

## Nightly auto-sync / auto-post

Use the CLI command:

```bash
flask --app run.py nightly-jobs
```

Example cron (Linux):

```bash
0 2 * * * cd /path/to/roman_bookkeeping && /path/to/.venv/bin/flask --app run.py nightly-jobs
```

## Notes / TODO

- TODO: replace plain-text passwords with hashed auth before production.
- TODO: if needed, replace 30-day monthly approximation with exact calendar month logic for recurring postings.
