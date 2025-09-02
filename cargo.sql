from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)
DB = "cargo.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- BOOKINGS ----------------
@app.route("/booking", methods=["POST"])
def add_booking():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (bilty_no, sender_name, receiver_name, vehicle_no, driver_name, driver_phone, weight, quantity, price, remarks, pickup_location, drop_location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data["bilty_no"], data["sender_name"], data["receiver_name"], data["vehicle_no"],
         data["driver_name"], data["driver_phone"], data["weight"], data["quantity"],
         data["price"], data["remarks"], data["pickup_location"], data["drop_location"]))
    conn.commit()
    return jsonify({"message": "Booking added successfully"}), 201

@app.route("/booking", methods=["GET"])
def get_bookings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings")
    rows = cursor.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/booking/<int:id>", methods=["GET"])
def get_booking(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE id=?", (id,))
    row = cursor.fetchone()
    return jsonify(dict(row)) if row else jsonify({"error": "Not found"}), 404

# ---------------- ACCOUNTS ----------------
@app.route("/accounts", methods=["POST"])
def add_account_entry():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (booking_id, debit, credit, remarks)
        VALUES (?, ?, ?, ?)""",
        (data["booking_id"], data.get("debit", 0), data.get("credit", 0), data["remarks"]))
    conn.commit()
    return jsonify({"message": "Account entry added"}), 201

@app.route("/accounts", methods=["GET"])
def get_accounts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts")
    rows = cursor.fetchall()
    return jsonify([dict(r) for r in rows])

# ---------------- GODOWN ----------------
@app.route("/godown", methods=["POST"])
def add_godown_entry():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO godowns (booking_id, stock_in, stock_out)
        VALUES (?, ?, ?)""",
        (data["booking_id"], data.get("stock_in", 0), data.get("stock_out", 0)))
    conn.commit()
    return jsonify({"message": "Godown entry added"}), 201

@app.route("/godown", methods=["GET"])
def get_godowns():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM godowns")
    rows = cursor.fetchall()
    return jsonify([dict(r) for r in rows])

# ---------------- DAYBOOK ----------------
@app.route("/daybook", methods=["POST"])
def add_daybook_entry():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO daybook (booking_id, description, amount)
        VALUES (?, ?, ?)""",
        (data["booking_id"], data["description"], data["amount"]))
    conn.commit()
    return jsonify({"message": "Daybook entry added"}), 201

@app.route("/daybook", methods=["GET"])
def get_daybook():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daybook")
    rows = cursor.fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    # Run server
    app.run(debug=True)

