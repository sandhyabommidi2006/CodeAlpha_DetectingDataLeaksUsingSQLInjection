
from flask import Flask, render_template, request, redirect, session, url_for, send_file
import sqlite3
import os
import qrcode

from cryptography.fernet import Fernet

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

app = Flask(__name__)
app.secret_key = "database_secret"

# ---------------------------------
# Paths
# ---------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(BASE_DIR, "database.db")
QR_FOLDER = os.path.join(BASE_DIR, "static", "qr")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")

os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# ---------------------------------
# Encryption Key
# ---------------------------------
with open(os.path.join(BASE_DIR, "secret.key"), "rb") as f:
    key = f.read()

cipher = Fernet(key)

# ---------------------------------
# Database Connection
# ---------------------------------
def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------
# Home
# ---------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------------------------
# Register
# ---------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        email = cipher.encrypt(email.encode())
        phone = cipher.encrypt(phone.encode())

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users
            (username,email,phone,password)
            VALUES(?,?,?,?)
        """, (username, email, phone, password))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------------------------
# Login
# ---------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE username=? AND password=?
        """, (username, password))

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")

# ---------------------------------
# Dashboard
# ---------------------------------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    conn.close()

    email = cipher.decrypt(user["email"]).decode()
    phone = cipher.decrypt(user["phone"]).decode()

    return render_template(
        "dashboard.html",
        username=user["username"],
        email=email,
        phone=phone
    )

# ---------------------------------
# Logout
# ---------------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

# ==========================================
# Bus Booking Page
# ==========================================

@app.route("/booking")
def booking():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM buses
        ORDER BY id
    """)

    buses = cursor.fetchall()

    conn.close()

    return render_template(
        "booking.html",
        buses=buses
    )


# ==========================================
# Seat Selection
# ==========================================

@app.route("/seats/<int:bus_id>")
def seats(bus_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM buses WHERE id=?",
        (bus_id,)
    )

    bus = cursor.fetchone()

    if bus is None:
        conn.close()
        return "Bus not found."

    cursor.execute("""
        SELECT *
        FROM seats
        WHERE bus_id=?
        ORDER BY seat_number
    """, (bus_id,))

    seats = cursor.fetchall()

    conn.close()

    return render_template(
        "seats.html",
        bus=bus,
        seats=seats
    )


# ==========================================
# Book Seat
# ==========================================

@app.route("/book/<int:bus_id>/<seat_number>")
def book(bus_id, seat_number):

    if "user_id" not in session:
        return redirect(url_for("login"))

    return redirect(
        url_for(
            "payment",
            bus_id=bus_id,
            seat_number=seat_number
        )
    )


# ==========================================
# Payment Page
# ==========================================

@app.route("/payment/<int:bus_id>/<seat_number>")
def payment(bus_id, seat_number):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM buses WHERE id=?",
        (bus_id,)
    )

    bus = cursor.fetchone()

    conn.close()

    if bus is None:
        return "Bus not found."

    return render_template(
        "payment.html",
        bus=bus,
        seat_number=seat_number
    )


# ==========================================
# Confirm Booking
# ==========================================

@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():

    if "user_id" not in session:
        return redirect(url_for("login"))

    bus_id = request.form["bus_id"]
    seat_number = request.form["seat_number"]

    conn = get_connection()
    cursor = conn.cursor()

    # Check seat availability
    cursor.execute("""
        SELECT status
        FROM seats
        WHERE bus_id=? AND seat_number=?
    """, (bus_id, seat_number))

    seat = cursor.fetchone()

    if seat is None:
        conn.close()
        return "Seat not found."

    if seat["status"] == "Booked":
        conn.close()
        return "Seat already booked."

    # Get fare
    cursor.execute(
        "SELECT fare FROM buses WHERE id=?",
        (bus_id,)
    )

    fare = cursor.fetchone()["fare"]

    # Save booking
    cursor.execute("""
        INSERT INTO bookings
        (
            user_id,
            bus_id,
            seat_number,
            fare,
            payment_status,
            ticket_status
        )
        VALUES
        (?,?,?,?,?,?)
    """,
    (
        session["user_id"],
        bus_id,
        seat_number,
        fare,
        "Paid",
        "Confirmed"
    ))

    booking_id = cursor.lastrowid

    # Update seat
    cursor.execute("""
        UPDATE seats
        SET status='Booked'
        WHERE bus_id=? AND seat_number=?
    """, (bus_id, seat_number))

    conn.commit()
    conn.close()

    return redirect(
        url_for(
            "ticket",
            booking_id=booking_id
        )
    )

# ==========================================
# Ticket Page
# ==========================================

@app.route("/ticket/<int:booking_id>")
def ticket(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            bookings.id,
            bookings.seat_number,
            bookings.fare,
            bookings.payment_status,
            bookings.ticket_status,
            buses.bus_name,
            buses.source,
            buses.destination,
            users.username
        FROM bookings
        JOIN buses
            ON bookings.bus_id = buses.id
        JOIN users
            ON bookings.user_id = users.id
        WHERE bookings.id=?
    """, (booking_id,))

    ticket = cursor.fetchone()

    conn.close()

    if ticket is None:
        return "Ticket not found."

    # -------------------------
    # Generate QR Code
    # -------------------------
    qr_data = (
        f"CloudRide E-Ticket\n"
        f"Booking ID : {ticket['id']}\n"
        f"Passenger : {ticket['username']}\n"
        f"Bus : {ticket['bus_name']}\n"
        f"Route : {ticket['source']} -> {ticket['destination']}\n"
        f"Seat : {ticket['seat_number']}\n"
        f"Fare : ₹{ticket['fare']}\n"
        f"Payment : {ticket['payment_status']}\n"
        f"Status : {ticket['ticket_status']}"
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=4
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    qr_filename = f"{booking_id}.png"

    qr_path = os.path.join(QR_FOLDER, qr_filename)

    img.save(qr_path)

    return render_template(
        "ticket.html",
        ticket=ticket,
        qr_image=qr_filename
    )


# ==========================================
# My Bookings
# ==========================================

@app.route("/my_bookings")
def my_bookings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            bookings.id,
            buses.bus_name,
            buses.source,
            buses.destination,
            bookings.seat_number,
            bookings.fare,
            bookings.ticket_status
        FROM bookings
        JOIN buses
            ON bookings.bus_id = buses.id
        WHERE bookings.user_id=?
        ORDER BY bookings.id DESC
    """, (session["user_id"],))

    bookings = cursor.fetchall()

    conn.close()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )

# ==========================================
# Download Ticket PDF
# ==========================================

@app.route("/download_ticket/<int:booking_id>")
def download_ticket(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            bookings.id,
            bookings.seat_number,
            bookings.fare,
            bookings.payment_status,
            bookings.ticket_status,
            buses.bus_name,
            buses.source,
            buses.destination,
            users.username
        FROM bookings
        JOIN buses
            ON bookings.bus_id = buses.id
        JOIN users
            ON bookings.user_id = users.id
        WHERE bookings.id=?
    """, (booking_id,))

    ticket = cursor.fetchone()
    conn.close()

    if ticket is None:
        return "Ticket not found."

    pdf_path = os.path.join(
        REPORT_FOLDER,
        f"Ticket_{booking_id}.pdf"
    )

    doc = SimpleDocTemplate(pdf_path)

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b><font size='18'>CloudRide E-Ticket</font></b>",
            styles["Title"]
        )
    )

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    data = [
        ["Passenger", ticket["username"]],
        ["Booking ID", str(ticket["id"])],
        ["Bus", ticket["bus_name"]],
        ["Route", f"{ticket['source']} → {ticket['destination']}"],
        ["Seat", ticket["seat_number"]],
        ["Fare", f"₹ {ticket['fare']}"],
        ["Payment", ticket["payment_status"]],
        ["Status", ticket["ticket_status"]],
    ]

    table = Table(data, colWidths=[2.2 * inch, 3.8 * inch])

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("BACKGROUND", (1, 0), (1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)

    doc.build(story)

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"CloudRide_Ticket_{booking_id}.pdf"
    )


# ==========================================
# Cancel Ticket
# ==========================================

@app.route("/cancel_ticket/<int:booking_id>")
def cancel_ticket(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT bus_id, seat_number
        FROM bookings
        WHERE id=?
    """, (booking_id,))

    booking = cursor.fetchone()

    if booking:

        cursor.execute("""
            UPDATE bookings
            SET ticket_status='Cancelled'
            WHERE id=?
        """, (booking_id,))

        cursor.execute("""
            UPDATE seats
            SET status='Available'
            WHERE bus_id=? AND seat_number=?
        """, (
            booking["bus_id"],
            booking["seat_number"]
        ))

        conn.commit()

    conn.close()

    return redirect(url_for("my_bookings"))


# ==========================================
# Run Application
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)