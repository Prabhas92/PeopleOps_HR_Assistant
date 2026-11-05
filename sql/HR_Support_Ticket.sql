CREATE TABLE IF NOT EXISTS peopleopsproject.genai_book.hr_support_tickets (
    ticket_id STRING,
    emp_id STRING,
    employee_name STRING,
    employee_email STRING,
    category STRING,
    subject STRING,
    description STRING,
    priority STRING,
    status STRING,
    created_at TIMESTAMP,
    email_status STRING
)
USING DELTA;

SELECT * FROM peopleopsproject.genai_book.hr_support_tickets;
