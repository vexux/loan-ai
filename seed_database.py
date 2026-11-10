"""
Run this once to create and seed the local SQLite banking database.
Usage: python seed_database.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "banking.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Drop existing tables to refresh schema
    cur.execute("DROP TABLE IF EXISTS application_events")
    cur.execute("DROP TABLE IF EXISTS loan_applications")
    cur.execute("DROP TABLE IF EXISTS accounts")
    cur.execute("DROP TABLE IF EXISTS customers")

    # --- 1. Customers Table ---
    cur.execute("""
    CREATE TABLE customers (
        customer_id      TEXT PRIMARY KEY,
        name             TEXT NOT NULL,
        email            TEXT,
        phone            TEXT,
        age              INTEGER NOT NULL,
        employment_type  TEXT NOT NULL,
        salary           REAL,
        credit_score     INTEGER,
        account_status   TEXT DEFAULT 'active',
        kyc_verified     INTEGER DEFAULT 1
    )
    """)

    cur.executemany("""
    INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?)
    """, [
        ("C001", "Alice Sharma", "alice@example.com", "+91-9000000001", 28, "Salaried",      75000,  720, "active",   1),
        ("C002", "Bob Mehta",    "bob@example.com",   "+91-9000000002", 19, "Salaried",      45000,  580, "active",   1),
        ("C003", "Carol Singh",  "carol@example.com", "+91-9000000003", 35, "Self-Employed", 120000, 810, "active",   1),
        ("C004", "David Kumar",  "david@example.com", "+91-9000000004", 42, "Salaried",      30000,  490, "active",   0),
        ("C005", "Eve Patel",    "eve@example.com",   "+91-9000000005", 52, "Salaried",      95000,  760, "inactive", 1),
        ("C006", "Frank Dsouza", "frank@example.com", "+91-9000000006", 31, "NRI",           150000, 740, "active",   1),
    ])

    # --- 2. Loan Applications Table (With Idempotency & Status) ---
    cur.execute("""
    CREATE TABLE loan_applications (
        application_id   TEXT PRIMARY KEY,
        customer_id      TEXT NOT NULL,
        loan_type        TEXT NOT NULL,
        loan_amount      REAL NOT NULL,
        tenure_months    INTEGER NOT NULL,
        purpose          TEXT,
        status           TEXT DEFAULT 'SUBMITTED',
        applied_on       TEXT NOT NULL,
        idempotency_key  TEXT UNIQUE,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)

    # --- 3. Application Events Table (Event Audit & Rollback Verification) ---
    cur.execute("""
    CREATE TABLE application_events (
        event_id         TEXT PRIMARY KEY,
        event_type       TEXT NOT NULL,
        application_id   TEXT NOT NULL,
        customer_id      TEXT NOT NULL,
        loan_type        TEXT NOT NULL,
        payload_json     TEXT NOT NULL,
        created_at       TEXT NOT NULL,
        trace_id         TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES loan_applications(application_id)
    )
    """)

    # --- 4. Accounts Table ---
    cur.execute("""
    CREATE TABLE accounts (
        account_id      TEXT PRIMARY KEY,
        customer_id     TEXT NOT NULL,
        account_type    TEXT,
        balance         REAL,
        currency        TEXT DEFAULT 'INR',
        status          TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)

    cur.executemany("""
    INSERT INTO accounts VALUES (?,?,?,?,?,?)
    """, [
        ("A001", "C001", "savings",  150000, "INR", "active"),
        ("A002", "C001", "current",  500000, "INR", "active"),
        ("A003", "C002", "savings",  25000,  "INR", "active"),
        ("A004", "C003", "savings",  300000, "INR", "active"),
        ("A005", "C004", "savings",  5000,   "INR", "active"),
    ])

    conn.commit()
    conn.close()
    print(f" Database successfully initialized at: {DB_PATH}")
    print("   Tables: customers, loan_applications, application_events, accounts")


if __name__ == "__main__":
    seed()
