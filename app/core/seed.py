"""Auto-seed the database on first startup.

Runs after table creation. If the database is empty (no stations),
it creates a minimum working dataset so the system is usable immediately.
This is safe to run on every startup — it exits early if data already exists.
"""
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.station import Station
from app.models.gate import Gate
from app.models.department import Department
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.driver import Driver

logger = logging.getLogger(__name__)


def seed_if_empty():
    db: Session = SessionLocal()
    try:
        # Already seeded?
        if db.query(Station).count() > 0:
            return

        logger.info("Seeding database with default data…")

        # --- Stations ---
        stations = [
            Station(name="Upper Tana", code="UT", latitude=-0.7500, longitude=37.1500, radius_meters=5000),
            Station(name="Wanjii",     code="WJ", latitude=-0.9500, longitude=37.2000, radius_meters=3000),
            Station(name="Sagana",     code="SG", latitude=-0.6700, longitude=37.2000, radius_meters=3000),
            Station(name="Mirira",     code="MR", latitude=-0.7800, longitude=37.1800, radius_meters=2000),
            Station(name="Mesco",      code="MS", latitude=-0.9200, longitude=37.2500, radius_meters=3000),
        ]
        db.add_all(stations)
        db.commit()

        # --- Gates ---
        gates = [
            Gate(name="Upper Tana Main Entrance", code="GATE-UT-01", station_id=1),
            Gate(name="Upper Tana Second Gate",   code="GATE-UT-02", station_id=1),
            Gate(name="Wanjii Main Entrance",     code="GATE-WJ-01", station_id=2),
            Gate(name="Wanjii Second Gate",       code="GATE-WJ-02", station_id=2),
            Gate(name="Sagana Main Entrance",     code="GATE-SG-01", station_id=3),
            Gate(name="Mirira Main Entrance",     code="GATE-MR-01", station_id=4),
            Gate(name="Mirira Second Gate",       code="GATE-MR-02", station_id=4),
            Gate(name="Mesco Main Entrance",      code="GATE-MS-01", station_id=5),
            Gate(name="Mesco Second Gate",        code="GATE-MS-02", station_id=5),
        ]
        db.add_all(gates)
        db.commit()

        # --- Departments ---
        departments = [
            Department(name="Transport",    code="TRN"),
            Department(name="ICT",          code="ICT"),
            Department(name="Procurement",  code="PROC"),
            Department(name="Engineering",  code="ENG"),
            Department(name="Operations",   code="OPS"),
            Department(name="Finance",      code="FIN"),
            Department(name="HR",           code="HR"),
            Department(name="Administration", code="ADMIN"),
            Department(name="Security",     code="SEC"),
        ]
        db.add_all(departments)
        db.commit()

        # --- Vehicles ---
        vehicles = [
            Vehicle(registration_number="KAA 123X", make="Toyota",   model="Hilux",         year=2020, home_station_id=1, fuel_type="Diesel", current_odometer=124532, traccar_device_id="KAA123X"),
            Vehicle(registration_number="KCA 234B", make="Toyota",   model="Hilux",         year=2019, home_station_id=1, fuel_type="Diesel", current_odometer=142800),
            Vehicle(registration_number="KCB 345C", make="Nissan",   model="Navara",        year=2021, home_station_id=1, fuel_type="Diesel", current_odometer=87300),
            Vehicle(registration_number="KCC 456D", make="Toyota",   model="Land Cruiser",  year=2018, home_station_id=1, fuel_type="Diesel", current_odometer=198400),
            Vehicle(registration_number="KCD 567E", make="Isuzu",    model="D-Max",         year=2022, home_station_id=1, fuel_type="Diesel", current_odometer=45200),
            Vehicle(registration_number="KCE 678F", make="Toyota",   model="Hilux",         year=2020, home_station_id=2, fuel_type="Diesel", current_odometer=76300),
            Vehicle(registration_number="KCG 890H", make="Toyota",   model="Hilux",         year=2021, home_station_id=3, fuel_type="Diesel", current_odometer=58900),
            Vehicle(registration_number="KFH 901J", make="Nissan",   model="Navara",        year=2019, home_station_id=5, fuel_type="Diesel", current_odometer=112700),
        ]
        db.add_all(vehicles)
        db.commit()

        # --- Drivers ---
        drivers = [
            Driver(staff_number="KGN7700", full_name="John Munyua",    phone="0722000001", employment_type="permanent", duty_station_id=1, license_number="DL-123456", license_expiry=date(2027, 6, 30)),
            Driver(staff_number="KGN7701", full_name="Ian Huy",        phone="0722000002", employment_type="contract",  duty_station_id=2, license_number="DL-234567", license_expiry=date(2026, 12, 15)),
            Driver(staff_number="KGN7702", full_name="Peter Njoroge",  phone="0722000003", employment_type="permanent", duty_station_id=1, license_number="DL-345678", license_expiry=date(2028, 3, 20), is_supervisor=True),
        ]
        db.add_all(drivers)
        db.commit()

        # --- Users ---
        # First user created is admin
        users = [
            User(staff_number="KGN0001", full_name="Symo (Admin)", role="admin",       password_hash=hash_password("staff123")),
            User(staff_number="KGN0002", full_name="Alice Wanjiku", role="supervisor",  station_id=1, password_hash=hash_password("staff123")),
            User(staff_number="KGN0004", full_name="John Munyua",   role="driver",      station_id=1, driver_id=1, password_hash=hash_password("staff123")),
        ]
        db.add_all(users)
        db.commit()

        # --- Gate users (one per gate) ---
        gate_users = [
            User(staff_number="GATE-UT-01", full_name="Upper Tana Gate 1 Duty", role="gatekeeper", station_id=1, gate_id=1, password_hash=hash_password("gate123")),
            User(staff_number="GATE-UT-02", full_name="Upper Tana Gate 2 Duty", role="gatekeeper", station_id=1, gate_id=2, password_hash=hash_password("gate123")),
            User(staff_number="GATE-WJ-01", full_name="Wanjii Gate 1 Duty",     role="gatekeeper", station_id=2, gate_id=3, password_hash=hash_password("gate123")),
            User(staff_number="GATE-WJ-02", full_name="Wanjii Gate 2 Duty",     role="gatekeeper", station_id=2, gate_id=4, password_hash=hash_password("gate123")),
            User(staff_number="GATE-SG-01", full_name="Sagana Gate 1 Duty",     role="gatekeeper", station_id=3, gate_id=5, password_hash=hash_password("gate123")),
            User(staff_number="GATE-MR-01", full_name="Mirira Gate 1 Duty",     role="gatekeeper", station_id=4, gate_id=6, password_hash=hash_password("gate123")),
            User(staff_number="GATE-MR-02", full_name="Mirira Gate 2 Duty",     role="gatekeeper", station_id=4, gate_id=7, password_hash=hash_password("gate123")),
            User(staff_number="GATE-MS-01", full_name="Mesco Gate 1 Duty",      role="gatekeeper", station_id=5, gate_id=8, password_hash=hash_password("gate123")),
            User(staff_number="GATE-MS-02", full_name="Mesco Gate 2 Duty",      role="gatekeeper", station_id=5, gate_id=9, password_hash=hash_password("gate123")),
        ]
        db.add_all(gate_users)
        db.commit()

        logger.info("Database seeded: %d stations, %d gates, %d vehicles, %d drivers, %d users",
                    len(stations), len(gates), len(vehicles), len(drivers), len(users) + len(gate_users))

    except Exception as e:
        db.rollback()
        logger.exception("Seed failed: %s", e)
    finally:
        db.close()