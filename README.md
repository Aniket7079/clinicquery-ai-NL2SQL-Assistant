
# ClinicQuery AI 🏥
  
An AI-powered Natural Language to SQL (NL2SQL) chatbot that allows users to query a clinic database using plain English.
      
## 🚀 Features..
- Convert natural language to SQL queries
- FastAPI backend
- SQLite database with synthetic healthcare data
- Data visualization using Plotly
- Safe SQL execution (SELECT-only)
- Agent-based architecture using Vanna AI 2.0

## 🛠️ Tech Stack  
- Python
- FastAPI
- SQLite
- Vanna AI
- Plotly
- Uvicorn

## 📊 Dataset
Synthetic clinic dataset including:
- Patients
- Doctors
- Appointments
- Treatments
- Invoices

## ▶️ How to Run
```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
python setup_database.py
uvicorn main:app --reload
=======
# clinicquery-ai-NL2SQL-Assistant
AI-powered NL2SQL chatbot using FastAPI and Vanna AI
>>>>>>> 853c837785704017f10f4816cd2845a9f98c9e35
