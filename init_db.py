import sqlite3
import os

# ==========================
# Database Path
# ==========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

# Delete old database (optional during development)
if os.path.exists(DATABASE):
    os.remove(DATABASE)

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# ==========================
# Users Table
# ==========================

cursor.execute("""
CREATE TABLE users(

id INTEGER PRIMARY KEY AUTOINCREMENT,

username TEXT UNIQUE NOT NULL,

password TEXT NOT NULL,

email BLOB NOT NULL,

phone BLOB NOT NULL

)
""")

# ==========================
# Buses Table
# ==========================

cursor.execute("""
CREATE TABLE buses(

id INTEGER PRIMARY KEY AUTOINCREMENT,

bus_name TEXT NOT NULL,

source TEXT NOT NULL,

destination TEXT NOT NULL,

fare INTEGER NOT NULL

)
""")

# ==========================
# Seats Table
# ==========================

cursor.execute("""
CREATE TABLE seats(

id INTEGER PRIMARY KEY AUTOINCREMENT,

bus_id INTEGER,

seat_number TEXT,

status TEXT,

FOREIGN KEY(bus_id)
REFERENCES buses(id)

)
""")

# ==========================
# Bookings Table
# ==========================

cursor.execute("""
CREATE TABLE bookings(

id INTEGER PRIMARY KEY AUTOINCREMENT,

user_id INTEGER,

bus_id INTEGER,

seat_number TEXT,

fare INTEGER,

payment_status TEXT,

ticket_status TEXT,

qr_token TEXT,

FOREIGN KEY(user_id)
REFERENCES users(id),

FOREIGN KEY(bus_id)
REFERENCES buses(id)

)
""")

# ==========================
# Insert Sample Buses
# ==========================

cursor.execute("""
INSERT INTO buses
(bus_name,source,destination,fare)
VALUES
('Cloud Express',
'Visakhapatnam',
'Vijayawada',
550)
""")

cursor.execute("""
INSERT INTO buses
(bus_name,source,destination,fare)
VALUES
('Cloud Deluxe',
'Visakhapatnam',
'Hyderabad',
950)
""")

# ==========================
# Seat Layout
# ==========================

seat_names = [

"A1","A2","A3","A4",

"B1","B2","B3","B4",

"C1","C2","C3","C4",

"D1","D2","D3","D4",

"E1","E2","E3","E4"

]

# Bus 1

for seat in seat_names:

    cursor.execute(

        "INSERT INTO seats(bus_id,seat_number,status) VALUES(?,?,?)",

        (1,seat,"Available")

    )

# Bus 2

for seat in seat_names:

    cursor.execute(

        "INSERT INTO seats(bus_id,seat_number,status) VALUES(?,?,?)",

        (2,seat,"Available")

    )

conn.commit()

conn.close()

print("===================================")
print("CloudRide Database Created")
print(DATABASE)
print("===================================")