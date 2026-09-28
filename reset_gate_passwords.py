import bcrypt
import sqlite3

NEW_PASSWORD = "gate123"

conn = sqlite3.connect("kfleet.db")
users = conn.execute(
    "SELECT id, staff_number FROM users WHERE role = 'gatekeeper'"
).fetchall()

if not users:
    print("No gatekeeper users found.")
else:
    new_hash = bcrypt.hashpw(
        NEW_PASSWORD.encode("utf-8")[:72],
        bcrypt.gensalt()
    ).decode("utf-8")

    for uid, staff in users:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, uid))
        print(f"Reset password for {staff}")

    conn.commit()
    print(f"\nDone. {len(users)} gate accounts now use password: {NEW_PASSWORD}")
    print("This hash is written to kfleet.db and will survive restarts.")

conn.close()