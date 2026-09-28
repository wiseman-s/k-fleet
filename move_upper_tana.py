import sqlite3

conn = sqlite3.connect("kfleet.db")
conn.execute(
    "UPDATE stations SET latitude = ?, longitude = ?, radius_meters = ? WHERE name = ?",
    (-0.9218, 36.9686, 20000.0, "Upper Tana")
)
conn.commit()

row = conn.execute(
    "SELECT id, name, latitude, longitude, radius_meters FROM stations WHERE name = 'Upper Tana'"
).fetchone()
print("Updated:", row)

conn.close()
print("\nUpper Tana is now centered on your current phone location with a 20 km radius.")
print("Vehicle KAA 123X will be considered inside the zone.")