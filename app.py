from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- DB Helper ---
def get_db():
    conn = sqlite3.connect("cargo.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialize Tables ---
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Booking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bilty_no INTEGER UNIQUE,
        date TEXT,
        sender TEXT,
        receiver TEXT,
        vehicle_no TEXT,
        driver_name TEXT,
        driver_phone TEXT,
        weight REAL,
        quantity INTEGER,
        price REAL,
        remarks TEXT,
        pickup TEXT,
        drop_loc TEXT
    )
    """)

    # Accounts / Invoices
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

    # Daybook
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daybook(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        type TEXT,
        ref_no TEXT,
        description TEXT,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- BOOKING ----------------
@app.route("/api/booking", methods=["POST"])
def add_booking():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT MAX(bilty_no) FROM bookings")
    last_bilty = cur.fetchone()[0]
    next_bilty = (last_bilty + 1) if last_bilty else 1001
    today = datetime.today().strftime("%Y-%m-%d")

    cur.execute("""
        INSERT INTO bookings 
        (bilty_no,date,sender,receiver,vehicle_no,driver_name,driver_phone,weight,quantity,price,remarks,pickup,drop_loc)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (next_bilty, today, data["sender"], data["receiver"], data["vehicle_no"], 
          data["driver_name"], data["driver_phone"], data["weight"], 
          data["quantity"], data["price"], data["remarks"], data["pickup"], data["drop_loc"]))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "bilty_no": next_bilty})

@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ---------------- ACCOUNTS ----------------
@app.route("/api/invoice", methods=["POST"])
def add_invoice():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT MAX(invoice_no) FROM invoices")
    last_no = cur.fetchone()[0]
    next_no = (last_no + 1) if last_no else 1001
    today = datetime.today().strftime("%Y-%m-%d")

    cur.execute("INSERT INTO invoices (invoice_no,date,party_name,description,amount) VALUES (?,?,?,?,?)",
                (next_no, today, data["party_name"], data["description"], data["amount"]))
    
    # Daybook entry
    cur.execute("INSERT INTO daybook (date,type,ref_no,description,amount) VALUES (?,?,?,?,?)",
                (today, "Invoice", str(next_no), data["description"], data["amount"]))

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
    cur.execute("SELECT date,description,amount as debit,NULL as credit FROM invoices WHERE party_name=? ORDER BY date", (party,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ---------------- DAYBOOK ----------------
@app.route("/api/daybook", methods=["GET"])
def get_daybook():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM daybook ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ---------------- GODOWN ----------------
@app.route("/api/godown", methods=["GET"])
def get_godown():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT bilty_no as bilty, sender as party, 'Goods' as item, quantity as qtyIn, 0 as qtyOut FROM bookings")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
