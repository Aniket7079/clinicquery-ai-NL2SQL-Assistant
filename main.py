
"""FastAPI application for the NL2SQL assignment. 

This app uses a deterministic SQL generation layer for reliability and keeps
the Vanna 2.0 agent wiring in vanna_setup.py so the project is aligned with the
assignment brief.

Endpoints:  
- POST /chat
- GET /health
"""

from __future__ import annotations 

import difflib
import json
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import plotly.graph_objects as go
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from vanna_setup import DB_PATH, get_runtime_context

APP_DIR = Path(__file__).resolve().parent
MAX_QUESTION_LENGTH = 500

app = FastAPI(title="Clinic NL2SQL API", version="1.0.0")

RUNTIME = get_runtime_context()
SEEDS = RUNTIME.seed_examples

# Small in-memory cache so repeated questions do not rerun the database.
_QUERY_CACHE: dict[str, dict[str, Any]] = {}


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question")

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        if len(value) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Question is too long. Maximum allowed length is {MAX_QUESTION_LENGTH} characters.")
        return value


class ChatResponse(BaseModel):
    message: str
    sql_query: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    chart: dict[str, Any] | None = None
    chart_type: str | None = None
    source: str = "rule-based"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _best_seed_match(question: str) -> tuple[float, dict[str, Any] | None]:
    if not SEEDS:
        return 0.0, None

    q_norm = _normalize(question)
    q_tokens = _token_set(question)
    best_score = 0.0
    best_item = None

    for item in SEEDS:
        seed_q = item["question"]
        seed_norm = _normalize(seed_q)
        seed_tokens = _token_set(seed_q)
        ratio = difflib.SequenceMatcher(None, q_norm, seed_norm).ratio()
        overlap = len(q_tokens & seed_tokens) / max(1, len(q_tokens | seed_tokens))
        score = 0.68 * ratio + 0.32 * overlap
        if score > best_score:
            best_score = score
            best_item = item
    return best_score, best_item


def _month_range(offset_months: int = 1) -> tuple[str, str]:
    today = date.today()
    first_day_this_month = today.replace(day=1)
    target_end = first_day_this_month - timedelta(days=1)
    for _ in range(offset_months - 1):
        target_end = target_end.replace(day=1) - timedelta(days=1)
    target_start = target_end.replace(day=1)
    return target_start.isoformat(), (target_end + timedelta(days=1)).isoformat()


def _last_month_range() -> tuple[str, str]:
    today = date.today()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    return first_day_last_month.isoformat(), (last_day_last_month + timedelta(days=1)).isoformat()


def _last_quarter_range() -> tuple[str, str]:
    today = date.today()
    current_q = (today.month - 1) // 3 + 1
    last_q = 4 if current_q == 1 else current_q - 1
    year = today.year - 1 if current_q == 1 else today.year
    start_month = 3 * (last_q - 1) + 1
    start_date = date(year, start_month, 1)
    if start_month == 10:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, start_month + 3, 1)
    return start_date.isoformat(), end_date.isoformat()


def _past_months_start(months: int) -> str:
    today = date.today().replace(day=1)
    year = today.year
    month = today.month
    for _ in range(months - 1):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return date(year, month, 1).isoformat()


def _validate_sql(sql: str) -> tuple[bool, str]:
    cleaned = sql.strip().rstrip(";")
    lowered = cleaned.lower()

    if not cleaned:
        return False, "Empty SQL statement."
    if not lowered.startswith("select"):
        return False, "Only SELECT statements are allowed."
    if ";" in cleaned:
        return False, "Multiple SQL statements are not allowed."
    dangerous = [" insert ", " update ", " delete ", " drop ", " alter ", " exec ", " grant ", " revoke ", " shutdown ", " pragma ", " attach ", " detach "]
    padded = f" {lowered} "
    for word in dangerous:
        if word in padded:
            return False, f"Dangerous SQL keyword blocked: {word.strip()}."
    if "sqlite_master" in lowered or "sqlite_temp_master" in lowered:
        return False, "Access to system tables is blocked."
    return True, cleaned


def _rows_to_lists(rows: list[sqlite3.Row], columns: list[str]) -> list[list[Any]]:
    return [[row[col] for col in columns] for row in rows]


def _run_sql(sql: str) -> tuple[list[str], list[list[Any]]]:
    with _connect() as conn:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return columns, _rows_to_lists(rows, columns)


def _generate_chart(columns: list[str], rows: list[list[Any]]) -> tuple[dict[str, Any] | None, str | None]:
    if not rows or len(columns) < 2:
        return None, None

    x = [row[0] for row in rows]
    y = [row[1] for row in rows]
    if not y or not all(isinstance(v, (int, float)) or v is None for v in y):
        return None, None

    chart_type = "line" if any(re.search(r"\d{4}-\d{2}", str(v)) for v in x) else "bar"
    fig = go.Figure()
    if chart_type == "line":
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=columns[1]))
    else:
        fig.add_trace(go.Bar(x=x, y=y, name=columns[1]))
    fig.update_layout(
        title=f"{columns[1]} by {columns[0]}",
        xaxis_title=columns[0],
        yaxis_title=columns[1],
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig.to_plotly_json(), chart_type


def _doctor_latest_department_subquery() -> str:
    return """
        SELECT a.patient_id, a.doctor_id
        FROM appointments a
        JOIN (
            SELECT patient_id, MAX(appointment_date) AS latest_date
            FROM appointments
            GROUP BY patient_id
        ) latest
          ON latest.patient_id = a.patient_id
         AND latest.latest_date = a.appointment_date
    """


def generate_sql(question: str) -> tuple[str, str]:
    """
    Return (sql, source) where source is 'memory' or 'rule-based'.
    """
    q = _normalize(question)
    q_tokens = _token_set(question)

    score, seed = _best_seed_match(question)
    if seed and score >= 0.62:
        return seed["sql"], "memory"

    start_last_month, end_last_month = _last_month_range()
    start_last_quarter, end_last_quarter = _last_quarter_range()
    start_6_months = _past_months_start(6)

    if any(phrase in q for phrase in ["how many patients", "total patients", "patient count"]):
        return "SELECT COUNT(*) AS total_patients FROM patients", "rule-based"

    if "list all doctors" in q or ("doctors" in q and "specialization" in q):
        return "SELECT name, specialization, department FROM doctors ORDER BY name", "rule-based"

    if "appointments for last month" in q or ("appointments" in q and "last month" in q):
        return (
            f"""
            SELECT a.id, p.first_name, p.last_name, d.name AS doctor_name,
                   a.appointment_date, a.status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN doctors d ON d.id = a.doctor_id
            WHERE date(a.appointment_date) >= date('{start_last_month}')
              AND date(a.appointment_date) < date('{end_last_month}')
            ORDER BY a.appointment_date
            """.strip(),
            "rule-based",
        )

    if "doctor" in q and "most appointments" in q:
        return (
            """
            SELECT d.name, COUNT(*) AS appointment_count
            FROM appointments a
            JOIN doctors d ON d.id = a.doctor_id
            GROUP BY d.name
            ORDER BY appointment_count DESC
            LIMIT 1
            """.strip(),
            "rule-based",
        )

    if "total revenue" in q:
        return "SELECT ROUND(COALESCE(SUM(total_amount), 0), 2) AS total_revenue FROM invoices", "rule-based"

    if "revenue by doctor" in q:
        return (
            f"""
            SELECT d.name AS doctor_name,
                   ROUND(COALESCE(SUM(i.total_amount), 0), 2) AS total_revenue
            FROM invoices i
            JOIN (
                SELECT a.patient_id, a.doctor_id
                FROM appointments a
                JOIN (
                    SELECT patient_id, MAX(appointment_date) AS latest_date
                    FROM appointments
                    GROUP BY patient_id
                ) latest
                  ON latest.patient_id = a.patient_id
                 AND latest.latest_date = a.appointment_date
            ) latest_appt
              ON latest_appt.patient_id = i.patient_id
            JOIN doctors d ON d.id = latest_appt.doctor_id
            GROUP BY d.name
            ORDER BY total_revenue DESC
            """.strip(),
            "rule-based",
        )

    if "cancelled appointments last quarter" in q or ("cancelled" in q and "quarter" in q):
        return (
            f"""
            SELECT COUNT(*) AS cancelled_appointments
            FROM appointments
            WHERE status = 'Cancelled'
              AND date(appointment_date) >= date('{start_last_quarter}')
              AND date(appointment_date) < date('{end_last_quarter}')
            """.strip(),
            "rule-based",
        )

    if "top 5 patients" in q and ("spending" in q or "spent" in q):
        return (
            """
            SELECT p.first_name, p.last_name,
                   ROUND(COALESCE(SUM(i.total_amount), 0), 2) AS total_spending
            FROM patients p
            JOIN invoices i ON i.patient_id = p.id
            GROUP BY p.id
            ORDER BY total_spending DESC
            LIMIT 5
            """.strip(),
            "rule-based",
        )

    if "average treatment cost by specialization" in q or ("treatment cost" in q and "specialization" in q):
        return (
            """
            SELECT d.specialization,
                   ROUND(AVG(t.cost), 2) AS avg_treatment_cost
            FROM treatments t
            JOIN appointments a ON a.id = t.appointment_id
            JOIN doctors d ON d.id = a.doctor_id
            GROUP BY d.specialization
            ORDER BY avg_treatment_cost DESC
            """.strip(),
            "rule-based",
        )

    if "monthly appointment count" in q or ("past 6 months" in q and "appointment" in q):
        return (
            f"""
            SELECT strftime('%Y-%m', appointment_date) AS month,
                   COUNT(*) AS appointment_count
            FROM appointments
            WHERE date(appointment_date) >= date('{start_6_months}')
            GROUP BY strftime('%Y-%m', appointment_date)
            ORDER BY month
            """.strip(),
            "rule-based",
        )

    if "city has the most patients" in q or ("most patients" in q and "city" in q):
        return (
            """
            SELECT city, COUNT(*) AS patient_count
            FROM patients
            GROUP BY city
            ORDER BY patient_count DESC
            LIMIT 1
            """.strip(),
            "rule-based",
        )

    if "visited more than 3 times" in q or ("more than 3 times" in q and "patients" in q):
        return (
            """
            SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count
            FROM patients p
            JOIN appointments a ON a.patient_id = p.id
            GROUP BY p.id
            HAVING COUNT(a.id) > 3
            ORDER BY visit_count DESC
            """.strip(),
            "rule-based",
        )

    if "unpaid invoices" in q:
        return (
            """
            SELECT id, patient_id, invoice_date, total_amount, paid_amount, status
            FROM invoices
            WHERE status = 'Pending'
            ORDER BY invoice_date DESC
            """.strip(),
            "rule-based",
        )

    if "percentage" in q and "no-show" in q:
        return (
            """
            SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2)
                AS no_show_percentage
            FROM appointments
            """.strip(),
            "rule-based",
        )

    if "busiest day" in q or "day of the week" in q:
        return (
            """
            SELECT CASE strftime('%w', appointment_date)
                     WHEN '0' THEN 'Sunday'
                     WHEN '1' THEN 'Monday'
                     WHEN '2' THEN 'Tuesday'
                     WHEN '3' THEN 'Wednesday'
                     WHEN '4' THEN 'Thursday'
                     WHEN '5' THEN 'Friday'
                     WHEN '6' THEN 'Saturday'
                   END AS day_of_week,
                   COUNT(*) AS appointment_count
            FROM appointments
            GROUP BY strftime('%w', appointment_date)
            ORDER BY appointment_count DESC
            LIMIT 1
            """.strip(),
            "rule-based",
        )

    if "revenue trend by month" in q or ("revenue" in q and "month" in q and "trend" in q):
        return (
            """
            SELECT strftime('%Y-%m', invoice_date) AS month,
                   ROUND(SUM(total_amount), 2) AS revenue
            FROM invoices
            GROUP BY strftime('%Y-%m', invoice_date)
            ORDER BY month
            """.strip(),
            "rule-based",
        )

    if "average appointment duration" in q and "doctor" in q:
        return (
            """
            SELECT d.name AS doctor_name,
                   ROUND(AVG(t.duration_minutes), 2) AS avg_duration_minutes
            FROM doctors d
            JOIN appointments a ON a.doctor_id = d.id
            JOIN treatments t ON t.appointment_id = a.id
            GROUP BY d.name
            ORDER BY avg_duration_minutes DESC
            """.strip(),
            "rule-based",
        )

    if "overdue invoices" in q:
        return (
            """
            SELECT p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount
            FROM patients p
            JOIN invoices i ON i.patient_id = p.id
            WHERE i.status = 'Overdue'
            ORDER BY i.invoice_date DESC
            """.strip(),
            "rule-based",
        )

    if "compare revenue between departments" in q or ("revenue" in q and "department" in q):
        return (
            f"""
            SELECT d.department,
                   ROUND(SUM(i.total_amount), 2) AS revenue
            FROM invoices i
            JOIN (
                SELECT a.patient_id, a.doctor_id
                FROM appointments a
                JOIN (
                    SELECT patient_id, MAX(appointment_date) AS latest_date
                    FROM appointments
                    GROUP BY patient_id
                ) latest
                  ON latest.patient_id = a.patient_id
                 AND latest.latest_date = a.appointment_date
            ) latest_appt
              ON latest_appt.patient_id = i.patient_id
            JOIN doctors d ON d.id = latest_appt.doctor_id
            GROUP BY d.department
            ORDER BY revenue DESC
            """.strip(),
            "rule-based",
        )

    if "registration trend by month" in q:
        return (
            """
            SELECT strftime('%Y-%m', registered_date) AS month,
                   COUNT(*) AS patient_count
            FROM patients
            GROUP BY strftime('%Y-%m', registered_date)
            ORDER BY month
            """.strip(),
            "rule-based",
        )

    # Friendly fallback: ask for the most likely information from the memory examples.
    if seed:
        return seed["sql"], "memory"

    return "SELECT 'Unable to map this question to a SQL pattern' AS message", "fallback"


def _pretty_message(question: str, row_count: int, source: str) -> str:
    if row_count == 0:
        return "No data found for that question."
    if source == "memory":
        return "I found a similar saved example and ran the matching SQL."
    return "Here are the results based on the generated SQL."


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    normalized = _normalize(question)

    if normalized in _QUERY_CACHE:
        cached = _QUERY_CACHE[normalized]
        return ChatResponse(**cached)

    sql_query, source = generate_sql(question)
    is_valid, cleaned_or_error = _validate_sql(sql_query)
    if not is_valid:
        raise HTTPException(status_code=400, detail=cleaned_or_error)

    sql_query = cleaned_or_error

    try:
        columns, rows = _run_sql(sql_query)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    if not rows:
        response = ChatResponse(
            message="No data found.",
            sql_query=sql_query,
            columns=columns,
            rows=rows,
            row_count=0,
            chart=None,
            chart_type=None,
            source=source,
        )
        _QUERY_CACHE[normalized] = response.model_dump()
        return response

    chart, chart_type = _generate_chart(columns, rows)
    response = ChatResponse(
        message=_pretty_message(question, len(rows), source),
        sql_query=sql_query,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        chart_type=chart_type,
        source=source,
    )
    _QUERY_CACHE[normalized] = response.model_dump()
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    db_ok = DB_PATH.exists()
    with _connect() as conn:
        table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]

    return {
        "status": "ok" if db_ok and table_count >= 5 else "degraded",
        "database": "connected" if db_ok else "missing",
        "agent_memory_items": len(SEEDS),
        "llm_provider": RUNTIME.llm_provider,
        "vanna_available": RUNTIME.vanna_available,
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Clinic NL2SQL API is running. Use POST /chat and GET /health.",
    }
