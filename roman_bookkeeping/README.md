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
- Scheduler DB path: `instance/scheduler.sqlite3` by default, or set `SCHEDULER_DB_PATH`

No scheduler data is edited by this app. It reads scheduler tables and upserts into bookkeeping import tables.

## Expected scheduler tables in v1

- `invoices` with columns:
  - `id, customer_id, job_id, invoice_number, invoice_date, due_date, subtotal, tax_amount, total_amount, status, updated_at`
- `payments` with columns:
  - `id, invoice_id, customer_id, job_id, payment_date, amount, method, reference_no, updated_at`

If your existing scheduler schema differs, adjust `app/sync_service.py` mappings.

---

## Windows quick start (PowerShell)

From `roman_bookkeeping` folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py run
```

Then open:

- URL: `http://127.0.0.1:5000/login`
- Username: `admin`
- Password: `admin123`

### If PowerShell blocks script activation

Run once in **PowerShell as Administrator**:

```powershell
Set-ExecutionPolicy RemoteSigned
```

Or run commands from `cmd.exe` using:

```cmd
.venv\Scripts\python -m flask --app run.py run
```

---

## Linux/macOS quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py run
```

---

## Windows: set scheduler DB path

Example PowerShell:

```powershell
$env:SCHEDULER_DB_PATH = "C:\path\to\scheduler.sqlite3"
python -m flask --app run.py run
```

For a permanent user-level variable:

```powershell
setx SCHEDULER_DB_PATH "C:\path\to\scheduler.sqlite3"
```

Open a new terminal after `setx`.

---

## Nightly auto-sync / auto-post

Use the CLI command:

```bash
python -m flask --app run.py nightly-jobs
```

### Windows Task Scheduler suggestion

Program/script:

```text
C:\path\to\roman_bookkeeping\.venv\Scripts\python.exe
```

Arguments:

```text
-m flask --app run.py nightly-jobs
```

Start in:

```text
C:\path\to\roman_bookkeeping
```

You can also use the helper script `run_nightly_jobs.bat`.

---

## Notes / TODO

- TODO: replace plain-text passwords with hashed auth before production.
- TODO: if needed, replace 30-day monthly approximation with exact calendar month logic for recurring postings.
