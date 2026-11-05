# Databricks notebook source
# MAGIC %pip install --upgrade databricks-langchain langchain-core langgraph

# COMMAND ----------

dbutils.library.restartPython()

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

from databricks_langchain import (
    VectorSearchRetrieverTool,
    DatabricksEmbeddings
)

# Use the same embedding endpoint used to create document embeddings
embedding_model = DatabricksEmbeddings(
    endpoint="databricks-gte-large-en"
)

# Connect to your existing AI Search index
hr_policy_tool = VectorSearchRetrieverTool(
    index_name="peopleopsproject.genai_book.hr_docs_vs_index_v2",
    embedding=embedding_model,
    text_column="chunk_text",
    columns=["chunk_id", "doc_name", "chunk_text"],
    num_results=3,
    query_type="HYBRID",
    tool_name="search_hr_policies",
    tool_description=(
        "Search HR policy documents, holiday calendars, "
        "leave rules, and company guidelines. "
        "Use this tool for questions about HR policies."
    )
)

print("HR policy retriever initialized successfully!")