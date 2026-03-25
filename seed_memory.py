
"""Seed the NL2SQL memory examples.

This script writes memory_seed.json, which the app loads on startup.
It is intentionally file-based so the examples persist across runs even when
using DemoAgentMemory (which is in-memory by design).
"""

from __future__ import annotations

import json
from pathlib import Path

SEED_PATH = Path(__file__).with_name("memory_seed.json")

SEEDS = [
  {
    "question": "How many patients do we have?",
    "sql": "SELECT COUNT(*) AS total_patients FROM patients",
    "tool_name": "run_sql"
  },
  {
    "question": "List all doctors and their specializations",
    "sql": "SELECT name, specialization, department FROM doctors ORDER BY name",
    "tool_name": "run_sql"
  },
  {
    "question": "Show me appointments for last month",
    "sql": "SELECT a.id, p.first_name, p.last_name, d.name AS doctor_name, a.appointment_date, a.status FROM appointments a JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id WHERE date(a.appointment_date) >= date('now','start of month','-1 month') AND date(a.appointment_date) < date('now','start of month') ORDER BY a.appointment_date",
    "tool_name": "run_sql"
  },
  {
    "question": "Which doctor has the most appointments?",
    "sql": "SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY appointment_count DESC LIMIT 1",
    "tool_name": "run_sql"
  },
  {
    "question": "What is the total revenue?",
    "sql": "SELECT ROUND(COALESCE(SUM(total_amount), 0), 2) AS total_revenue FROM invoices",
    "tool_name": "run_sql"
  },
  {
    "question": "Show revenue by doctor",
    "sql": "SELECT d.name AS doctor_name, ROUND(COALESCE(SUM(i.total_amount), 0), 2) AS total_revenue FROM invoices i JOIN appointments a ON a.patient_id = i.patient_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY total_revenue DESC",
    "tool_name": "run_sql"
  },
  {
    "question": "How many cancelled appointments last quarter?",
    "sql": "SELECT COUNT(*) AS cancelled_appointments FROM appointments WHERE status = 'Cancelled' AND date(appointment_date) >= date('now','start of month','-3 months') AND date(appointment_date) < date('now','start of month','-0 months')",
    "tool_name": "run_sql"
  },
  {
    "question": "Top 5 patients by spending",
    "sql": "SELECT p.first_name, p.last_name, ROUND(COALESCE(SUM(i.total_amount), 0), 2) AS total_spending FROM patients p JOIN invoices i ON i.patient_id = p.id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
    "tool_name": "run_sql"
  },
  {
    "question": "Average treatment cost by specialization",
    "sql": "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_treatment_cost DESC",
    "tool_name": "run_sql"
  },
  {
    "question": "Show monthly appointment count for the past 6 months",
    "sql": "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count FROM appointments WHERE date(appointment_date) >= date('now','start of month','-5 months') GROUP BY strftime('%Y-%m', appointment_date) ORDER BY month",
    "tool_name": "run_sql"
  },
  {
    "question": "Which city has the most patients?",
    "sql": "SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1",
    "tool_name": "run_sql"
  },
  {
    "question": "List patients who visited more than 3 times",
    "sql": "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count FROM patients p JOIN appointments a ON a.patient_id = p.id GROUP BY p.id HAVING COUNT(a.id) > 3 ORDER BY visit_count DESC",
    "tool_name": "run_sql"
  },
  {
    "question": "Show unpaid invoices",
    "sql": "SELECT id, patient_id, invoice_date, total_amount, paid_amount, status FROM invoices WHERE status = 'Pending' ORDER BY invoice_date DESC",
    "tool_name": "run_sql"
  },
  {
    "question": "What percentage of appointments are no-shows?",
    "sql": "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS no_show_percentage FROM appointments",
    "tool_name": "run_sql"
  },
  {
    "question": "Revenue trend by month",
    "sql": "SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount), 2) AS revenue FROM invoices GROUP BY strftime('%Y-%m', invoice_date) ORDER BY month",
    "tool_name": "run_sql"
  },
  {
    "question": "Average appointment duration by doctor",
    "sql": "SELECT d.name AS doctor_name, ROUND(AVG(t.duration_minutes), 2) AS avg_duration_minutes FROM doctors d JOIN appointments a ON a.doctor_id = d.id JOIN treatments t ON t.appointment_id = a.id GROUP BY d.name ORDER BY avg_duration_minutes DESC",
    "tool_name": "run_sql"
  },
  {
    "question": "List patients with overdue invoices",
    "sql": "SELECT p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount FROM patients p JOIN invoices i ON i.patient_id = p.id WHERE i.status = 'Overdue' ORDER BY i.invoice_date DESC",
    "tool_name": "run_sql"
  },
  {
    "question": "Compare revenue between departments",
    "sql": "SELECT d.department, ROUND(SUM(i.total_amount), 2) AS revenue FROM invoices i JOIN appointments a ON a.patient_id = i.patient_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.department ORDER BY revenue DESC",
    "tool_name": "run_sql"
  }
]

def main() -> None:
    SEED_PATH.write_text(json.dumps(SEEDS, indent=2), encoding="utf-8")
    print(f"Saved {len(SEEDS)} memory examples to {SEED_PATH.name}")

if __name__ == "__main__":
    main()
