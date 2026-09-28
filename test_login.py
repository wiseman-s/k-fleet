import bcrypt
import sqlite3

conn = sqlite3.connect("kfleet.db")

for staff in ["GATE-UT-01", "GATE-WJ-01"]:
    row = conn.execute(
        "SELECT id, staff_number, role, password_hash, is_active FROM users WHERE staff_number = ?",
        (staff,)
    ).fetchone()

    if not row:
        print(f"{staff}: NOT FOUND")
        continue

    uid, sn, role, ph, is_active = row
    print(f"\n{sn} (role={role}, id={uid}, active={is_active})")
    print(f"  hash starts: {ph[:30]}...")
    print(f"  hash length: {len(ph)}")

    try:
        ok = bcrypt.checkpw(b"gate123", ph.encode("utf-8"))
        print(f"  bcrypt.checkpw(b'gate123') → {ok}")
    except Exception as e:
        print(f"  bcrypt error: {type(e).__name__}: {e}")

# Also test the exact function the app uses
print("\n=== Testing via app.core.security.verify_password ===")
try:
    from app.core.security import verify_password
    for staff in ["GATE-UT-01", "GATE-WJ-01"]:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE staff_number = ?",
            (staff,)
        ).fetchone()
        if row:
            print(f"  {staff}: verify_password('gate123', hash) = {verify_password('gate123', row[0])}")
except Exception as e:
    print(f"  Could not import: {e}")

conn.close()