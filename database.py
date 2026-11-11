
import sqlite3
from datetime import datetime

DB_NAME = "food_donation.db"


# 1. Connect to database
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# 2. Create database tables
def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            donor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_name TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            expiry_time TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            claimed_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (donor_id) REFERENCES donors(donor_id)
        )
    """)

    conn.commit()
    conn.close()


# 3. Register donor - prevent duplicates
def register_donor(name, location, phone):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT donor_id
        FROM donors
        WHERE LOWER(TRIM(donor_name)) = LOWER(TRIM(?))
        AND LOWER(TRIM(location)) = LOWER(TRIM(?))
    """, (name, location))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return None

    cursor.execute("""
        INSERT INTO donors (donor_name, location, phone)
        VALUES (?, ?, ?)
    """, (name, location, phone))

    conn.commit()

    donor_id = cursor.lastrowid

    conn.close()

    return donor_id


# 4. Add donation - prevent duplicates
def add_donation(donor_id, food_name, quantity, unit, expiry_time):

    conn = get_connection()
    cursor = conn.cursor()

    expiry_string = expiry_time.isoformat()

    cursor.execute("""
        SELECT donation_id
        FROM donations
        WHERE donor_id = ?
        AND LOWER(TRIM(food_name)) = LOWER(TRIM(?))
        AND quantity = ?
        AND LOWER(TRIM(unit)) = LOWER(TRIM(?))
        AND expiry_time = ?
    """, (
        donor_id,
        food_name,
        quantity,
        unit,
        expiry_string
    ))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO donations
        (donor_id, food_name, quantity, unit, expiry_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        donor_id,
        food_name,
        quantity,
        unit,
        expiry_string,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return True


# 5. Get available donations
def get_available_donations():

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT donations.*, donors.donor_name, donors.location
        FROM donations
        JOIN donors ON donations.donor_id = donors.donor_id
        WHERE donations.status = 'Available'
    """)

    donations = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return donations


# 6. Claim donation
def claim_donation(donation_id, ngo_name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donations
        SET status = 'Claimed', claimed_by = ?
        WHERE donation_id = ? AND status = 'Available'
    """, (ngo_name, donation_id))

    success = cursor.rowcount == 1

    conn.commit()
    conn.close()

    return success


# 7. Update collection status
def update_status(donation_id, new_status):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donations
        SET status = ?
        WHERE donation_id = ? AND status = 'Claimed'
    """, (new_status, donation_id))

    success = cursor.rowcount == 1

    conn.commit()
    conn.close()

    return success


# 8. Get all donors
def get_donors():

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM donors")

    donors = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return donors


# 9. Get all donations
def get_all_donations():

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT donations.*, donors.donor_name, donors.location
        FROM donations
        JOIN donors ON donations.donor_id = donors.donor_id
        ORDER BY donations.created_at DESC
    """)

    donations = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return donations


# -----------------------------------------
# ACCOUNT OWNERSHIP OPERATIONS
# -----------------------------------------


# Get the donor profile linked to a logged-in user
def get_donor_id_for_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT donor_id
        FROM donors
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


# Get only donations belonging to a particular donor
def get_donations_by_donor(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT donations.*, donors.donor_name, donors.location
        FROM donations
        JOIN donors ON donations.donor_id = donors.donor_id
        WHERE donors.user_id = ?
        ORDER BY donations.created_at DESC
    """, (user_id,))

    result = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return result


# Donor can edit only their own available donations
def edit_donation_by_donor(
    donation_id, user_id, food_name,
    quantity, unit, expiry_time
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donations
        SET food_name = ?,
            quantity = ?,
            unit = ?,
            expiry_time = ?
        WHERE donation_id = ?
        AND status = 'Available'
        AND donor_id IN (
            SELECT donor_id
            FROM donors
            WHERE user_id = ?
        )
    """, (
        food_name.strip(),
        quantity,
        unit,
        expiry_time.isoformat(),
        donation_id,
        user_id
    ))

    success = cursor.rowcount == 1
    conn.commit()
    conn.close()

    return success


# Donor can delete only their own available donations
def delete_donation_by_donor(donation_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM donations
        WHERE donation_id = ?
        AND status = 'Available'
        AND donor_id IN (
            SELECT donor_id
            FROM donors
            WHERE user_id = ?
        )
    """, (donation_id, user_id))

    success = cursor.rowcount == 1
    conn.commit()
    conn.close()

    return success


# Collector can claim an available donation
def claim_donation_by_collector(
    donation_id, collector_user_id, collector_name
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donations
        SET status = 'Claimed',
            claimed_by = ?,
            claimed_by_user_id = ?
        WHERE donation_id = ?
        AND status = 'Available'
    """, (
        collector_name,
        collector_user_id,
        donation_id
    ))

    success = cursor.rowcount == 1
    conn.commit()
    conn.close()

    return success


# Get only the donations claimed by this collector
def get_donations_by_collector(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT donations.*, donors.donor_name, donors.location
        FROM donations
        JOIN donors ON donations.donor_id = donors.donor_id
        WHERE donations.claimed_by_user_id = ?
        ORDER BY donations.created_at DESC
    """, (user_id,))

    result = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return result


# Collector can update only their own claimed donations
def update_collection_by_collector(
    donation_id, collector_user_id, new_status
):
    if new_status not in ("Collected", "Cancelled"):
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donations
        SET status = ?
        WHERE donation_id = ?
        AND claimed_by_user_id = ?
        AND status = 'Claimed'
    """, (
        new_status,
        donation_id,
        collector_user_id
    ))

    success = cursor.rowcount == 1
    conn.commit()
    conn.close()

    return success
