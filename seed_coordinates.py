import sqlite3

conn = sqlite3.connect("kfleet.db")

coordinates = {
    "Upper Tana":  (-0.7500, 37.1500, 5000.0),
    "Wanjii":      (-0.9500, 37.2000, 3000.0),
    "Sagana":      (-0.6700, 37.2000, 3000.0),
    "Mirira":      (-0.7800, 37.1800, 2000.0),
    "Mesco":       (-0.9200, 37.2500, 3000.0),
}

for name, (lat, lng, radius) in coordinates.items():
    row = conn.execute("SELECT id FROM stations WHERE name = ?", (name,)).fetchone()
    if not row:
        print(f"Skipping {name} — not found in database")
        continue
    conn.execute(
        "UPDATE stations SET latitude = ?, longitude = ?, radius_meters = ? WHERE id = ?",
        (lat, lng, radius, row[0])
    )
    print(f"Set {name}: {lat}, {lng} · radius {radius:.0f} m")

conn.commit()
conn.close()
print("\nDone.")