from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("cargo.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return render_template("booking.html")  # default page

# Save booking (from booking.html)
@app.route("/add_booking", methods=["POST"])
def add_booking():
    data = request.get_json()
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (bilty_no, sender_name, receiver_name, date)
            VALUES (?, ?, ?, DATE('now'))
        """, (data["bilty_no"], data["sender_name"], data["receiver_name"]))
        conn.commit()
        conn.close()
        return "✅ Booking Saved!"
    except Exception as e:
        return f"❌ Error: {e}"

# Get booking (for details.html)
@app.route("/get_booking/<bilty_no>")
def get_booking(bilty_no):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE bilty_no=?", (bilty_no,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "Booking not found"})

if __name__ == "__main__":
    app.run(debug=True)
# Insert this into your existing app.py where you have get_db or similar helper
from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "cargo.db")

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Utility: ensure accounts tables exist ----------
def init_accounts_tables():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        phone TEXT,
        email TEXT,
        notes TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        party_name TEXT,
        description TEXT,
        amount REAL,
        status TEXT DEFAULT 'Unpaid'
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        party_name TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
    )""")
    conn.commit()
    conn.close()

# Call once on startup
init_accounts_tables()

# ---------- API: Create Invoice (and auto ledger post) ----------
@app.route("/api/invoice", methods=["POST"])
def api_create_invoice():
    data = request.get_json()
    # expected fields: invoice_no, party_name, description, amount, post_type
    # post_type: "DebitParty" or "CreditParty" indicating how ledger should be recorded
    invoice_no = data.get("invoice_no")
    party_name = data.get("party_name")
    description = data.get("description", "")
    amount = float(data.get("amount", 0) or 0)

    if not invoice_no or not party_name or amount <= 0:
        return jsonify({"status":"error","message":"invoice_no, party_name and positive amount required"}), 400

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO invoices (invoice_no, party_name, description, amount)
            VALUES (?, ?, ?, ?)
        """, (invoice_no, party_name, description, amount))
        invoice_id = cur.lastrowid

        # Auto-post ledger:
        # We'll record two ledger entries (double-entry simple):
        # 1) Party ledger: debit = amount (party owes)  (or credit depending on business)
        # 2) Company account (Sales/Cash): credit = amount
        # For simplicity we will post:
        #   ledger_entries: party_name gets debit = amount
        #   ledger_entries: party_name = 'Company' gets credit = amount  (so you see both sides)
        # You can change logic to suit your chart of accounts.

        # Entry: party debit
        cur.execute("""
            INSERT INTO ledger_entries (invoice_id, party_name, description, debit, credit)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, party_name, f"Invoice {invoice_no}: {description}", amount, 0.0))

        # Entry: company credit
        cur.execute("""
            INSERT INTO ledger_entries (invoice_id, party_name, description, debit, credit)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, "Company", f"Invoice {invoice_no}", 0.0, amount))

        conn.commit()
        return jsonify({"status":"success","invoice_id": invoice_id}), 201
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({"status":"error","message":"Invoice number already exists or DB error","detail":str(e)}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"status":"error","message":str(e)}), 500
    finally:
        conn.close()

# ---------- API: List Invoices ----------
@app.route("/api/invoices", methods=["GET"])
def api_list_invoices():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices ORDER BY date DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ---------- API: Get single invoice ----------
@app.route("/api/invoice/<int:inv_id>", methods=["GET"])
def api_get_invoice(inv_id):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices WHERE id=?", (inv_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"error":"Not found"}), 404

# ---------- API: Delete Invoice (and related ledger entries) ----------
@app.route("/api/invoice/<int:inv_id>", methods=["DELETE"])
def api_delete_invoice(inv_id):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        # delete ledger entries linked to this invoice
        cur.execute("DELETE FROM ledger_entries WHERE invoice_id=?", (inv_id,))
        # delete invoice
        cur.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
        conn.commit()
        conn.close()
        return jsonify({"status":"success","message":"Invoice and ledger entries deleted"})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# ---------- API: Get Ledger for a Party  ----------
@app.route("/api/ledger/<party_name>", methods=["GET"])
def api_get_ledger(party_name):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, invoice_id, party_name, date, description, debit, credit
        FROM ledger_entries WHERE party_name=? ORDER BY date DESC
    """, (party_name,))
    rows = [dict(r) for r in cur.fetchall()]

    # compute balance
    balance = 0.0
    for r in reversed(rows):  # chronological
        balance += (r['debit'] or 0) - (r['credit'] or 0)

    conn.close()
    return jsonify({"entries": rows, "balance": balance})

# ---------- API: List Parties (with balances) ----------
@app.route("/api/parties", methods=["GET"])
def api_list_parties():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT party_name FROM ledger_entries")
    parties = [r[0] for r in cur.fetchall()]
    result = []
    for p in parties:
        cur.execute("SELECT SUM(debit) as total_debit, SUM(credit) as total_credit FROM ledger_entries WHERE party_name=?", (p,))
        s = cur.fetchone()
        total_debit = s["total_debit"] or 0
        total_credit = s["total_credit"] or 0
        balance = total_debit - total_credit
        result.append({"party_name": p, "balance": balance, "total_debit": total_debit, "total_credit": total_credit})
    conn.close()
    return jsonify(result)

# ---------- Optional: Manual ledger entry (debit/credit) ----------
@app.route("/api/ledger/manual", methods=["POST"])
def api_manual_ledger():
    data = request.get_json()
    party = data.get("party_name")
    desc = data.get("description","")
    debit = float(data.get("debit",0) or 0)
    credit = float(data.get("credit",0) or 0)
    if not party or (debit==0 and credit==0):
        return jsonify({"status":"error","message":"party_name and debit or credit required"}), 400
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ledger_entries (invoice_id, party_name, description, debit, credit)
        VALUES (?, ?, ?, ?, ?)
    """, (None, party, desc, debit, credit))
    conn.commit()
    conn.close()
    return jsonify({"status":"success"})
@app.route("/accounts")
def accounts_page():
    return render_template("accounts.html")
```)
from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- Database Helper ---
def get_db():
    conn = sqlite3.connect("cargo.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- Create Tables if not exist ---
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no INTEGER UNIQUE,
        date TEXT,
        party_name TEXT,
        description TEXT,
        amount REAL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Routes ---
@app.route("/")
def home():
    return render_template("accounts.html")

@app.route("/api/invoice", methods=["POST"])
def add_invoice():
    data = request.json
    conn = get_db()
    cur = conn.cursor()

    # Auto Invoice Number
    cur.execute("SELECT MAX(invoice_no) FROM invoices")
    last_no = cur.fetchone()[0]
    next_no = (last_no + 1) if last_no else 1001

    today = datetime.today().strftime("%Y-%m-%d")

    cur.execute("INSERT INTO invoices (invoice_no,date,party_name,description,amount) VALUES (?,?,?,?,?)",
                (next_no, today, data["party_name"], data["description"], data["amount"]))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "invoice_no": next_no})

@app.route("/api/invoices", methods=["GET"])
def get_invoices():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/invoice/<int:id>", methods=["DELETE"])
def delete_invoice(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM invoices WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route("/api/ledger/<party>", methods=["GET"])
def ledger(party):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT date,description,amount as debit, NULL as credit FROM invoices WHERE party_name=? ORDER BY date", (party,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)
