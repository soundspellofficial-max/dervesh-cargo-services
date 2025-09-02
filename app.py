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
