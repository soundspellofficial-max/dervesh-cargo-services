-- accounts.sql

-- Parties table (optional helper)
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    phone TEXT,
    email TEXT,
    notes TEXT
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT UNIQUE,
    date TEXT DEFAULT CURRENT_TIMESTAMP,
    party_name TEXT,
    description TEXT,
    amount REAL,
    status TEXT DEFAULT 'Unpaid'  -- Paid/Unpaid etc.
);

-- Ledger entries table
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,          -- nullable (can have manual ledger entries)
    party_name TEXT,
    date TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    debit REAL DEFAULT 0,        -- amount debited
    credit REAL DEFAULT 0,       -- amount credited
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
