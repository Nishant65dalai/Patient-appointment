"""
seed_data.py - loads the Day 10 sample dataset (10 doctors, 14
patients, 50 appointments) into hospital.db.

Run this once after starting the app for the first time:
    python seed_data.py

Safe to re-run - the .sql files DELETE existing rows first.
"""
import sqlite3
from pathlib import Path

from config import settings

conn = sqlite3.connect(settings.db_path)
conn.row_factory = sqlite3.Row

schema_sql = (Path(__file__).resolve().parent / "seed_sql" / "01_schema.sql").read_text()
seed_sql = (Path(__file__).resolve().parent / "seed_sql" / "02_seed_data.sql").read_text()

conn.executescript(schema_sql)
conn.executescript(seed_sql)
conn.commit()

n_doctors = conn.execute("SELECT COUNT(*) AS n FROM doctors").fetchone()["n"]
n_patients = conn.execute("SELECT COUNT(*) AS n FROM patients").fetchone()["n"]
n_appts = conn.execute("SELECT COUNT(*) AS n FROM appointments").fetchone()["n"]

conn.close()
print(f"Seed data loaded: {n_doctors} doctors, {n_patients} patients, "
      f"{n_appts} appointments.")
