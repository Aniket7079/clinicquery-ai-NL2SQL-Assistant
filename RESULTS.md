# Results
 
Validation run against the generated `clinic.db`.

**Passed:** 20 / 20 

## 1. How many patients do we have? 

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT COUNT(*) AS total_patients FROM patients
```
- **Result summary:** 1 row(s). total_patients=200

## 2. List all doctors and their specializations

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT name, specialization, department FROM doctors ORDER BY name
```
- **Result summary:** 15 row(s). name=Dr. Anil Vohra, specialization=Cardiology, department=Heart Care | name=Dr. Bhaskar Sood, specialization=Pediatrics, department=Child Care
 
## 3. Show me appointments for last month

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT a.id, p.first_name, p.last_name, d.name AS doctor_name, a.appointment_date, a.status FROM appointments a JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id WHERE date(a.appointment_date) >= date('now','start of month','-1 month') AND date(a.appointment_date) < date('now','start of month') ORDER BY a.appointment_date
```
- **Result summary:** 48 row(s). id=401, first_name=Gaurav, last_name=Khan, doctor_name=Dr. Girish Lal, appointment_date=2026-02-01 10:45:35, status=Cancelled | id=496, first_name=Chirag, last_name=Chawla, doctor_name=Dr. Farah Rana, appointment_date=2026-02-01 14:15:01, status=Completed

## 4. Which doctor has the most appointments?

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY appointment_count DESC LIMIT 1
```
- **Result summary:** 1 row(s). name=Dr. Farah Rana, appointment_count=69

## 5. What is the total revenue?

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT ROUND(COALESCE(SUM(total_amount), 0), 2) AS total_revenue FROM invoices
```
- **Result summary:** 1 row(s). total_revenue=1528125.66

## 6. Show revenue by doctor

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT d.name AS doctor_name, ROUND(COALESCE(SUM(i.total_amount), 0), 2) AS total_revenue FROM invoices i JOIN appointments a ON a.patient_id = i.patient_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY total_revenue DESC
```
- **Result summary:** 15 row(s). doctor_name=Dr. Anil Vohra, total_revenue=595931.44 | doctor_name=Dr. Farah Rana, total_revenue=529467.02

## 7. How many cancelled appointments last quarter?

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT COUNT(*) AS cancelled_appointments FROM appointments WHERE status = 'Cancelled' AND date(appointment_date) >= date('now','start of month','-3 months') AND date(appointment_date) < date('now','start of month','-0 months')
```
- **Result summary:** 1 row(s). cancelled_appointments=13

## 8. Top 5 patients by spending

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT p.first_name, p.last_name, ROUND(COALESCE(SUM(i.total_amount), 0), 2) AS total_spending FROM patients p JOIN invoices i ON i.patient_id = p.id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5
```
- **Result summary:** 5 row(s). first_name=Esha, last_name=Khan, total_spending=31723.23 | first_name=Zoya, last_name=Saxena, total_spending=30523.03

## 9. Average treatment cost by specialization

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_treatment_cost DESC
```
- **Result summary:** 5 row(s). specialization=Orthopedics, avg_treatment_cost=2634.9 | specialization=Dermatology, avg_treatment_cost=2630.41

## 10. Show monthly appointment count for the past 6 months

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count FROM appointments WHERE date(appointment_date) >= date('now','start of month','-5 months') GROUP BY strftime('%Y-%m', appointment_date) ORDER BY month
```
- **Result summary:** 6 row(s). month=2025-10, appointment_count=40 | month=2025-11, appointment_count=38

## 11. Which city has the most patients?

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1
```
- **Result summary:** 1 row(s). city=Mumbai, patient_count=24

## 12. List patients who visited more than 3 times

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count FROM patients p JOIN appointments a ON a.patient_id = p.id GROUP BY p.id HAVING COUNT(a.id) > 3 ORDER BY visit_count DESC
```
- **Result summary:** 57 row(s). first_name=Priya, last_name=Iyer, visit_count=13 | first_name=Nikhil, last_name=Iyer, visit_count=10

## 13. Show unpaid invoices

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT id, patient_id, invoice_date, total_amount, paid_amount, status FROM invoices WHERE status = 'Pending' ORDER BY invoice_date DESC
```
- **Result summary:** 53 row(s). id=203, patient_id=67, invoice_date=2026-03-21, total_amount=9984.21, paid_amount=4431.92, status=Pending | id=126, patient_id=174, invoice_date=2026-03-14, total_amount=8821.93, paid_amount=1452.06, status=Pending

## 14. What percentage of appointments are no-shows?

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS no_show_percentage FROM appointments
```
- **Result summary:** 1 row(s). no_show_percentage=8.6

## 15. Show the busiest day of the week for appointments

- **Status:** PASS
- **Generated SQL:**
```sql
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
```
- **Result summary:** 1 row(s). day_of_week=Sunday, appointment_count=83

## 16. Revenue trend by month

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount), 2) AS revenue FROM invoices GROUP BY strftime('%Y-%m', invoice_date) ORDER BY month
```
- **Result summary:** 13 row(s). month=2025-03, revenue=51251.01 | month=2025-04, revenue=151896.42

## 17. Average appointment duration by doctor

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT d.name AS doctor_name, ROUND(AVG(t.duration_minutes), 2) AS avg_duration_minutes FROM doctors d JOIN appointments a ON a.doctor_id = d.id JOIN treatments t ON t.appointment_id = a.id GROUP BY d.name ORDER BY avg_duration_minutes DESC
```
- **Result summary:** 15 row(s). doctor_name=Dr. Hina Lal, avg_duration_minutes=103.67 | doctor_name=Dr. Girish Lal, avg_duration_minutes=103.67 (uses treatments.duration_minutes as the closest available duration proxy)

## 18. List patients with overdue invoices

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount FROM patients p JOIN invoices i ON i.patient_id = p.id WHERE i.status = 'Overdue' ORDER BY i.invoice_date DESC
```
- **Result summary:** 40 row(s). first_name=Arjun, last_name=Singh, invoice_date=2026-03-23, total_amount=7589.94, paid_amount=1192.06 | first_name=Kabir, last_name=Tiwari, invoice_date=2026-03-13, total_amount=5256.64, paid_amount=1192.29

## 19. Compare revenue between departments

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT d.department, ROUND(SUM(i.total_amount), 2) AS revenue FROM invoices i JOIN appointments a ON a.patient_id = i.patient_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.department ORDER BY revenue DESC
```
- **Result summary:** 5 row(s). department=Heart Care, revenue=1032034.05 | department=Bone & Joint, revenue=957207.66

## 20. Show patient registration trend by month

- **Status:** PASS
- **Generated SQL:**
```sql
SELECT strftime('%Y-%m', registered_date) AS month,
                   COUNT(*) AS patient_count
            FROM patients
            GROUP BY strftime('%Y-%m', registered_date)
            ORDER BY month
```
- **Result summary:** 13 row(s). month=2025-03, patient_count=4 | month=2025-04, patient_count=16

## Notes

- Revenue-by-doctor and revenue-by-department queries map each patient to the latest doctor seen, because invoices are linked to patients rather than directly to doctors or departments.
- The assignment schema does not include a dedicated appointment duration column, so question 17 uses treatment duration as a proxy.
