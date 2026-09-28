import sqlite3

conn = sqlite3.connect("kfleet.db")

print("=== USERS ===")
for row in conn.execute("SELECT id, staff_number, full_name, role, station_id, gate_id FROM users"):
    print(row)

print()
print("=== GATES ===")
for row in conn.execute("SELECT id, name, code, station_id FROM gates"):
    print(row)

print()
print("=== GATE TRANSACTIONS (last 10) ===")
for row in conn.execute("SELECT id, gate_id, journey_id, transaction_type, odometer, notes, created_at FROM gate_transactions ORDER BY id DESC LIMIT 10"):
    print(row)

print()
print("=== ACTIVE JOURNEYS (approved or out) ===")
for row in conn.execute("SELECT id, journey_code, vehicle_id, driver_id, origin_station_id, status, destination FROM journeys WHERE status IN ('approved', 'out') ORDER BY id DESC"):
    print(row)

conn.close()