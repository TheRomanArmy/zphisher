PRAGMA foreign_keys = ON;

-- App users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'admin',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Minimal chart of accounts for bookkeeping.
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL, -- asset, liability, equity, income, expense
    category TEXT, -- e.g. overhead, direct_cost, service_income
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Imported invoices from scheduler system.
CREATE TABLE IF NOT EXISTS imported_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduler_invoice_id TEXT NOT NULL UNIQUE,
    customer_id TEXT,
    job_id TEXT,
    invoice_number TEXT,
    invoice_date TEXT NOT NULL,
    due_date TEXT,
    subtotal REAL NOT NULL DEFAULT 0,
    tax_amount REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0,
    status TEXT,
    source_updated_at TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Imported payments from scheduler system.
CREATE TABLE IF NOT EXISTS imported_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduler_payment_id TEXT NOT NULL UNIQUE,
    scheduler_invoice_id TEXT,
    customer_id TEXT,
    job_id TEXT,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT,
    reference_no TEXT,
    source_updated_at TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Manual + recurring-posted expense entries.
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date TEXT NOT NULL,
    vendor_name TEXT,
    description TEXT,
    amount REAL NOT NULL,
    account_id INTEGER,
    expense_type TEXT NOT NULL, -- overhead or direct_cost
    job_id TEXT,
    invoice_id TEXT,
    is_billable INTEGER NOT NULL DEFAULT 0,
    recurring_expense_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (recurring_expense_id) REFERENCES recurring_expenses(id)
);

-- Recurring templates to auto-post monthly expenses.
CREATE TABLE IF NOT EXISTS recurring_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    vendor_name TEXT,
    description TEXT,
    amount REAL NOT NULL,
    account_id INTEGER,
    expense_type TEXT NOT NULL,
    default_job_id TEXT,
    interval_unit TEXT NOT NULL DEFAULT 'monthly', -- monthly, weekly, yearly
    interval_value INTEGER NOT NULL DEFAULT 1,
    start_date TEXT NOT NULL,
    next_run_date TEXT NOT NULL,
    end_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Journal header table for simple double-entry expansion.
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,
    source_type TEXT NOT NULL, -- invoice_import, payment_import, expense, recurring_expense
    source_id TEXT,
    memo TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Journal lines (debit/credit) for each journal entry.
CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    line_type TEXT NOT NULL, -- debit, credit
    amount REAL NOT NULL,
    job_id TEXT,
    invoice_id TEXT,
    FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Logs for manual/nightly sync runs.
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL, -- invoices, payments, recurring_post, full
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'started', -- started, success, failed
    rows_processed INTEGER NOT NULL DEFAULT 0,
    message TEXT
);

-- Optional denormalized cache for quick job profitability snapshots.
CREATE TABLE IF NOT EXISTS job_profitability_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL UNIQUE,
    revenue_amount REAL NOT NULL DEFAULT 0,
    direct_cost_amount REAL NOT NULL DEFAULT 0,
    gross_profit REAL NOT NULL DEFAULT 0,
    margin_pct REAL,
    last_calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Seed one default admin user and starter accounts.
INSERT OR IGNORE INTO users (id, username, password, full_name, role)
VALUES (1, 'admin', 'admin123', 'Default Admin', 'admin');

INSERT OR IGNORE INTO accounts (code, name, account_type, category) VALUES
('4000', 'Service Income', 'income', 'service_income'),
('5000', 'Direct Job Materials', 'expense', 'direct_cost'),
('6100', 'Software Subscriptions', 'expense', 'overhead'),
('6110', 'Phone & Internet', 'expense', 'overhead'),
('6120', 'Insurance', 'expense', 'overhead');
