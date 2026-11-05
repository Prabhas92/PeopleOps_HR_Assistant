# Databricks notebook source
tables = [
    "peopleopsproject.genai_book.employees",
    "peopleopsproject.genai_book.leave_balance"
]

for table in tables:
    print(f"\n========== {table} ==========")
    spark.table(table).printSchema()

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT session_user() AS authenticated_user;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Python database tools (User Defined Functions)

# COMMAND ----------

identity = spark.sql("""
    SELECT current_user() AS email
""").first()["email"]

print("Authenticated identity:", identity)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Create the employee lookup tool

# COMMAND ----------

def get_my_employee_details():

    query = """
        SELECT
            emp_id,
            full_name,
            email,
            department,
            location,
            grade,
            join_date
        FROM peopleopsproject.genai_book.employees
        WHERE LOWER(email) = LOWER(:email)
    """

    result = spark.sql(
        query,
        args={"email": identity}
    )

    return [row.asDict() for row in result.collect()]

# COMMAND ----------

# MAGIC %md
# MAGIC #### Create the leave-balance tool

# COMMAND ----------

def get_my_leave_balance():

    query = """
        SELECT
            e.full_name,
            l.leave_type,
            l.entitled_days,
            l.carried_forward,
            l.used_days,
            l.balance_days,
            l.as_of_date
        FROM peopleopsproject.genai_book.employees e
        INNER JOIN peopleopsproject.genai_book.leave_balance l
            ON e.emp_id = l.emp_id
        WHERE LOWER(e.email) = LOWER(:email)
        ORDER BY l.leave_type
    """

    result = spark.sql(
        query,
        args={"email": identity}
    )

    return [row.asDict() for row in result.collect()]

# COMMAND ----------

# MAGIC %md
# MAGIC #### Test the UD functions

# COMMAND ----------

print("EMPLOYEE DETAILS")
print(get_my_employee_details())

print("\nLEAVE BALANCE")
print(get_my_leave_balance())

# COMMAND ----------

# MAGIC %md
# MAGIC #### We now have three independent capabilities:
# MAGIC 1. get_my_employee_details() — structured employee lookup.
# MAGIC 2. get_my_leave_balance() — structured leave information.
# MAGIC 3. hr_policy_tool — retrieves unstructured HR documents using AI Search.