# Databricks notebook source
# MAGIC %run ./00-Dependencies

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

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Register the Python functions as agent tools

# COMMAND ----------

import json
from langchain_core.tools import tool

@tool
def employee_details_tool() -> str:
    """Get the authenticated employee's own employee details."""
    result = get_my_employee_details()
    return json.dumps(result, default=str)


@tool
def leave_balance_tool() -> str:
    """Get the authenticated employee's own leave balances by leave type."""
    result = get_my_leave_balance()
    return json.dumps(result, default=str)


# Existing AI Search retriever from Stage 1
hr_search_tool = hr_policy_tool

# Combine all three tools
peopleops_tools = [
    employee_details_tool,
    leave_balance_tool,
    hr_search_tool
]

for t in peopleops_tools:
    print(t.name, "-", t.description)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Create the unified agent

# COMMAND ----------

# MAGIC %pip install --force-reinstall --no-deps langgraph-prebuilt==1.0.8

# COMMAND ----------

from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent

llm = ChatDatabricks(
    endpoint="databricks-gpt-oss-120b",
    temperature=0
)

system_prompt = """
You are the PeopleOps HR Assistant for Nimbus Analytics.

You have access to three tools:

1. employee_details_tool:
   Use for employee profile questions.

2. leave_balance_tool:
   Use for questions about available leave balances,
   used leaves, entitled leaves and leave types.

3. search_hr_policies:
   Use for HR policies, holiday calendars, company
   guidelines, leave rules and carry-forward policies.

Instructions:

- Identify the type of question before selecting a tool.
- Use the appropriate tool for factual employee or policy information.
- Do not invent employee information or leave balances.
- Do not invent HR policies or holiday dates.
- If a tool returns no data, clearly tell the employee.
- For questions requiring both employee data and policy information,
  use the relevant tools.
- Keep answers clear and concise.
- Never ask the employee to provide another employee's ID.
"""

peopleops_agent = create_react_agent(
    model=llm,
    tools=peopleops_tools,
    prompt=system_prompt
)

print("Unified PeopleOps agent created!")

# COMMAND ----------

identity = spark.sql(
        "SELECT current_user()"
    ).first()[0]

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
# MAGIC ### Test the Unifid Agent

# COMMAND ----------

test_questions = [
    "Show my employee details.",
    "How many earned leaves do I have?",
    "What are the holidays in Bengaluru for 2026?",
    "Show my leave balance and explain the leave types."
]

for question in test_questions:

    print("\n" + "=" * 70)
    print("QUESTION:", question)

    response = peopleops_agent.invoke({
        "messages": [
            {"role": "user", "content": question}
        ]
    })

    print("ANSWER:")
    print(response["messages"][-1].content)