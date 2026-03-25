
"""Create and populate the clinic SQLite database for the NL2SQL assignment.

Running this file creates/overwrites clinic.db in the project directory.
"""

from __future__ import annotations

import random
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).with_name("clinic.db")
SEED = 42

FIRST_NAMES = [
    "Aarav", "Aditi", "Aman", "Anaya", "Aniket", "Arjun", "Arya", "Bhavna",
    "Chirag", "Diya", "Esha", "Fatima", "Gaurav", "Harsh", "Ishita", "Ishaan",
    "Kabir", "Kavya", "Kiran", "Krishna", "Meera", "Mihir", "Neha", "Nikhil",
    "Nisha", "Om", "Pallavi", "Priya", "Rahul", "Rhea", "Rohit", "Sara",
    "Sanjay", "Simran", "Soham", "Tanvi", "Vijay", "Vivek", "Yash", "Zoya",
]

LAST_NAMES = [
    "Agrawal", "Bansal", "Chawla", "Deshmukh", "Gandhi", "Iyer", "Jain",
    "Kapoor", "Khan", "Kumar", "Mehta", "Mishra", "Nair", "Patel", "Pillai",
    "Reddy", "Shah", "Sharma", "Singh", "Verma", "Yadav", "Tiwari", "Joshi",
    "Kulkarni", "Thakur", "Saxena", "Sethi", "Bora", "Malhotra", "Bhatt",
]

CITIES = [
    "Pune", "Mumbai", "Nashik", "Nagpur", "Thane", "Aurangabad", "Solapur",
    "Ahmedabad", "Bengaluru", "Hyderabad",
]

SPECIALIZATIONS = [
    ("Dermatology", "Skin Care"),
    ("Cardiology", "Heart Care"),
    ("Orthopedics", "Bone & Joint"),
    ("General", "General Medicine"),
    ("Pediatrics", "Child Care"),
]

DOCTOR_FIRST_NAMES = [
    "Anil", "Bhaskar", "Chetan", "Deepa", "Eshwar", "Farah", "Girish", "Hina",
    "Irfan", "Jyoti", "Karan", "Leena", "Mohan", "Naina", "Ojas", "Pooja",
    "Rakesh", "Sana", "Tarun", "Usha", "Varun", "Wahid", "Yogesh", "Zeenat",
]

DOCTOR_LAST_NAMES = [
    "Ahuja", "Bhatia", "Chandra", "Dixit", "Gill", "Hegde", "Kapur", "Lal",
    "Menon", "Nambiar", "Oberoi", "Pandey", "Qureshi", "Rana", "Sood", "Trivedi",
    "Upadhyay", "Vohra", "Wagle", "Zaveri",
]

NOTES = [
    "Follow-up in two weeks.",
    "Patient advised to rest and hydrate.",
    "Prescribed routine medication.",
    "Recommend lab tests before next visit.",
    "Procedure completed without complications.",
    "Discussed lifestyle changes and diet.",
    "Referred for specialist consultation.",
    "Monitor symptoms and return if worsens.",
    "Vaccination completed.",
    "Mild symptoms, stable condition.",
    "Surgery scheduled next month.",
    "Review reports during next appointment.",
]

def daterange_days(start: date, end: date, rng: random.Random) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, delta))

def datetime_within_last_year(rng: random.Random) -> datetime:
    today = date.today()
    start = today - timedelta(days=365)
    day = daterange_days(start, today, rng)
    hour = rng.randint(8, 18)
    minute = rng.choice([0, 15, 30, 45])
    second = rng.randint(0, 59)
    return datetime(day.year, day.month, day.day, hour, minute, second)

def iso_date_from_days_ago(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()

def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        DROP TABLE IF EXISTS treatments;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS patients;
        DROP TABLE IF EXISTS doctors;

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            city TEXT,
            registered_date DATE
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE INDEX idx_patients_city ON patients(city);
        CREATE INDEX idx_appointments_patient ON appointments(patient_id);
        CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
        CREATE INDEX idx_appointments_date ON appointments(appointment_date);
        CREATE INDEX idx_invoices_patient ON invoices(patient_id);
        CREATE INDEX idx_treatments_appointment ON treatments(appointment_id);
        """
    )

def generate_doctors(rng: random.Random) -> list[dict]:
    doctors = []
    used_names = set()
    for spec, dept in SPECIALIZATIONS:
        for _ in range(3):
            while True:
                name = f"Dr. {rng.choice(DOCTOR_FIRST_NAMES)} {rng.choice(DOCTOR_LAST_NAMES)}"
                if name not in used_names:
                    used_names.add(name)
                    break
            doctors.append(
                {
                    "name": name,
                    "specialization": spec,
                    "department": dept,
                    "phone": f"+91-{rng.randint(70000, 99999)}-{rng.randint(10000, 99999)}",
                }
            )
    rng.shuffle(doctors)
    return doctors

def generate_patients(rng: random.Random, n: int = 200) -> list[dict]:
    patients = []
    used_names = set()
    today = date.today()
    for _ in range(n):
        while True:
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            key = (first, last)
            if key not in used_names:
                used_names.add(key)
                break
        gender = rng.choice(["M", "F"])
        age_days = rng.randint(18 * 365, 82 * 365)
        dob = today - timedelta(days=age_days)
        registered_days_ago = rng.randint(0, 365)
        registered_date = today - timedelta(days=registered_days_ago)
        email = None if rng.random() < 0.16 else f"{first.lower()}.{last.lower()}{rng.randint(1,99)}@example.com"
        phone = None if rng.random() < 0.12 else f"+91-{rng.randint(60000, 99999)}-{rng.randint(10000, 99999)}"
        patients.append(
            {
                "first_name": first,
                "last_name": last,
                "email": email,
                "phone": phone,
                "date_of_birth": dob.isoformat(),
                "gender": gender,
                "city": rng.choice(CITIES),
                "registered_date": registered_date.isoformat(),
            }
        )
    return patients

def weighted_choices(ids: list[int], rng: random.Random, weights: list[float], k: int) -> list[int]:
    return rng.choices(ids, weights=weights, k=k)

def generate_appointments(rng: random.Random, patient_ids: list[int], doctor_ids: list[int], n: int = 500) -> list[dict]:
    # A few repeat visitors and busier doctors make the data less uniform.
    patient_weights = []
    for pid in patient_ids:
        if pid <= 15:
            patient_weights.append(rng.uniform(3.0, 6.0))
        elif pid <= 60:
            patient_weights.append(rng.uniform(1.5, 3.0))
        else:
            patient_weights.append(rng.uniform(0.6, 1.4))

    doctor_weights = []
    for did in doctor_ids:
        if did in doctor_ids[:3]:
            doctor_weights.append(rng.uniform(2.5, 4.5))
        elif did in doctor_ids[3:9]:
            doctor_weights.append(rng.uniform(1.2, 2.2))
        else:
            doctor_weights.append(rng.uniform(0.7, 1.5))

    status_weights = [0.55, 0.25, 0.12, 0.08]
    statuses = ["Completed", "Scheduled", "Cancelled", "No-Show"]

    appts = []
    for _ in range(n):
        appt_dt = datetime_within_last_year(rng)
        appts.append(
            {
                "patient_id": rng.choices(patient_ids, weights=patient_weights, k=1)[0],
                "doctor_id": rng.choices(doctor_ids, weights=doctor_weights, k=1)[0],
                "appointment_date": appt_dt.isoformat(sep=" "),
                "status": rng.choices(statuses, weights=status_weights, k=1)[0],
                "notes": None if rng.random() < 0.33 else rng.choice(NOTES),
            }
        )
    return appts

def generate_treatments(rng: random.Random, appointment_ids: list[int], completed_appointment_ids: list[int], n: int = 350) -> list[dict]:
    treatments = []
    treatment_names = [
        "Consultation",
        "Blood Test",
        "X-Ray",
        "ECG",
        "Skin Screening",
        "Physiotherapy",
        "Vaccination",
        "Medication Review",
        "Ultrasound",
        "Minor Procedure",
        "Diet Counseling",
        "Follow-up Review",
    ]
    for _ in range(n):
        appointment_id = rng.choice(completed_appointment_ids)
        treatments.append(
            {
                "appointment_id": appointment_id,
                "treatment_name": rng.choice(treatment_names),
                "cost": round(rng.uniform(50, 5000), 2),
                "duration_minutes": rng.randint(10, 180),
            }
        )
    return treatments

def generate_invoices(rng: random.Random, patient_ids: list[int], n: int = 300) -> list[dict]:
    invoices = []
    statuses = ["Paid", "Pending", "Overdue"]
    status_weights = [0.65, 0.22, 0.13]
    today = date.today()
    for _ in range(n):
        total = round(rng.uniform(100, 10000), 2)
        status = rng.choices(statuses, weights=status_weights, k=1)[0]
        if status == "Paid":
            paid = total
        elif status == "Pending":
            paid = round(total * rng.uniform(0.0, 0.6), 2)
        else:
            paid = round(total * rng.uniform(0.0, 0.35), 2)
        invoices.append(
            {
                "patient_id": rng.choice(patient_ids),
                "invoice_date": (today - timedelta(days=rng.randint(0, 365))).isoformat(),
                "total_amount": total,
                "paid_amount": paid,
                "status": status,
            }
        )
    return invoices

def bulk_insert(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn.executemany(sql, ([row[col] for col in columns] for row in rows))

def main() -> None:
    rng = random.Random(SEED)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)

        doctors = generate_doctors(rng)
        bulk_insert(conn, "doctors", doctors)

        patients = generate_patients(rng, 200)
        bulk_insert(conn, "patients", patients)

        doctor_ids = [row[0] for row in conn.execute("SELECT id FROM doctors ORDER BY id")]
        patient_ids = [row[0] for row in conn.execute("SELECT id FROM patients ORDER BY id")]

        appointments = generate_appointments(rng, patient_ids, doctor_ids, 500)
        bulk_insert(conn, "appointments", appointments)

        completed_appointment_ids = [
            row[0] for row in conn.execute(
                "SELECT id FROM appointments WHERE status='Completed' ORDER BY id"
            )
        ]
        treatments = generate_treatments(rng, [row[0] for row in conn.execute("SELECT id FROM appointments")], completed_appointment_ids, 350)
        bulk_insert(conn, "treatments", treatments)

        invoices = generate_invoices(rng, patient_ids, 300)
        bulk_insert(conn, "invoices", invoices)

        conn.commit()

        summary = {
            "patients": conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
            "doctors": conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
            "appointments": conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
            "treatments": conn.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
            "invoices": conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        }
        print(
            f"Created {summary['patients']} patients, {summary['doctors']} doctors, "
            f"{summary['appointments']} appointments, {summary['treatments']} treatments, "
            f"{summary['invoices']} invoices in {DB_PATH.name}"
        )
    finally:
        conn.close()

if __name__ == "__main__":
    main()
