
import sqlite3
import hashlib
import secrets
import hmac

from database import get_connection


# Password hashing settings
ITERATIONS = 310000


# 1. Create account table and update existing tables
def initialize_accounts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('donor', 'collector')),
            display_name TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Add ownership columns to existing tables if needed
    donor_columns = [
        row[1] for row in cursor.execute(
            "PRAGMA table_info(donors)"
        ).fetchall()
    ]

    if "user_id" not in donor_columns:
        cursor.execute(
            "ALTER TABLE donors ADD COLUMN user_id INTEGER"
        )

    donation_columns = [
        row[1] for row in cursor.execute(
            "PRAGMA table_info(donations)"
        ).fetchall()
    ]

    if "claimed_by_user_id" not in donation_columns:
        cursor.execute(
            "ALTER TABLE donations ADD COLUMN claimed_by_user_id INTEGER"
        )

    conn.commit()
    conn.close()


# 2. Securely hash a password
def hash_password(password, salt):
    password_bytes = password.encode("utf-8")
    salt_bytes = bytes.fromhex(salt)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt_bytes,
        ITERATIONS
    )

    return password_hash.hex()


# 3. Register a new account
def register_account(username, password, role,
                     display_name, location, phone):

    username = username.strip()

    if not username or len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if role not in ("donor", "collector"):
        return False, "Invalid account role."

    salt = secrets.token_bytes(16).hex()
    password_hash = hash_password(password, salt)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users
            (username, password_hash, salt, role,
             display_name, location, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            username, password_hash, salt, role,
            display_name.strip(), location.strip(), phone.strip()
        ))

        user_id = cursor.lastrowid

        # Create the donor profile linked to this account
        if role == "donor":
            cursor.execute("""
                INSERT INTO donors
                (donor_name, location, phone, user_id)
                VALUES (?, ?, ?, ?)
            """, (
                display_name.strip(),
                location.strip(),
                phone.strip(),
                user_id
            ))

        conn.commit()
        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "That username already exists."

    finally:
        conn.close()


# 4. Verify login details
def login_account(username, password):

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users
        WHERE username = ?
    """, (username.strip(),))

    user = cursor.fetchone()
    conn.close()

    if user is None:
        return None

    entered_hash = hash_password(password, user["salt"])

    if hmac.compare_digest(entered_hash, user["password_hash"]):
        return dict(user)

    return None
