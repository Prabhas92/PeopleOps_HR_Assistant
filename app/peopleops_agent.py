
# =========================================================
# PEOPLEOPS HR ASSISTANT
# Databricks + LangGraph + AI Search + SQL + GPT OSS 120B
# =========================================================


# ---------------------------------------------------------
# 1. IMPORTS
# ---------------------------------------------------------

import json
import uuid

from datetime import datetime

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

from databricks_langchain import (
    ChatDatabricks,
    DatabricksEmbeddings,
    VectorSearchRetrieverTool,
)

from langchain.agents import create_agent
from langchain_core.tools import tool


# ---------------------------------------------------------
# 2. DATABRICKS CONFIGURATION
# ---------------------------------------------------------

EMPLOYEE_ID = "E1099"

SQL_WAREHOUSE_HTTP_PATH = (
    "/sql/1.0/warehouses/c27dbfdf73acc56c"
)

EMPLOYEES_TABLE = (
    "peopleopsproject.genai_book.employees"
)

LEAVE_BALANCE_TABLE = (
    "peopleopsproject.genai_book.leave_balance"
)

TICKETS_TABLE = (
    "peopleopsproject.genai_book.hr_support_tickets"
)

VECTOR_SEARCH_INDEX = (
    "peopleopsproject.genai_book.hr_docs_vs_index_v2"
)

LLM_ENDPOINT = "databricks-gpt-oss-120b"

EMBEDDING_ENDPOINT = "databricks-gte-large-en"


# ---------------------------------------------------------
# 3. DATABRICKS WORKSPACE CLIENT
# ---------------------------------------------------------

workspace_client = WorkspaceClient()


# ---------------------------------------------------------
# 4. SQL CONNECTION FUNCTION
# ---------------------------------------------------------

def run_query(query, parameters=None):
    """
    Execute SQL queries using the Databricks SQL Warehouse.
    Supports parameterized queries and returns results
    as a list of dictionaries.
    """

    cfg = Config()

    with sql.connect(
        server_hostname=cfg.host.replace("https://", ""),
        http_path=SQL_WAREHOUSE_HTTP_PATH,
        credentials_provider=lambda: cfg.authenticate,
    ) as connection:

        with connection.cursor() as cursor:

            if parameters is None:
                cursor.execute(query)
            else:
                cursor.execute(query, parameters)

            if cursor.description is None:
                return []

            columns = [
                column[0]
                for column in cursor.description
            ]

            rows = cursor.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]


# ---------------------------------------------------------
# 5. EMPLOYEE DETAILS SQL TOOL
# ---------------------------------------------------------

@tool
def employee_details_tool() -> str:
    """
    Retrieve employee profile information, including
    employee ID, name, email, department, location,
    manager ID, grade, and joining date.
    """

    query = f"""
        SELECT
            emp_id,
            full_name,
            email,
            department,
            location,
            manager_id,
            grade,
            join_date
        FROM {EMPLOYEES_TABLE}
        WHERE emp_id = ?
    """

    result = run_query(
        query,
        (EMPLOYEE_ID,)
    )

    return json.dumps(result, default=str)


# ---------------------------------------------------------
# 6. LEAVE BALANCE SQL TOOL
# ---------------------------------------------------------

@tool
def leave_balance_tool() -> str:
    """
    Retrieve employee leave balances, including
    leave type, entitled days, carried forward,
    used days, remaining balance, and as-of date.
    """

    query = f"""
        SELECT
            emp_id,
            leave_type,
            entitled_days,
            carried_forward,
            used_days,
            balance_days,
            as_of_date
        FROM {LEAVE_BALANCE_TABLE}
        WHERE emp_id = ?
        ORDER BY leave_type
    """

    result = run_query(
        query,
        (EMPLOYEE_ID,)
    )

    return json.dumps(result, default=str)


# ---------------------------------------------------------
# 7. HR TICKET CREATION TOOL
# ---------------------------------------------------------

@tool
def create_hr_ticket(
    category: str,
    subject: str,
    description: str,
    priority: str = "Medium",
) -> str:
    """
    Create an HR support ticket when an employee's
    question cannot be resolved using available
    employee data or HR policy documents.
    """

    # Retrieve employee information

    employee_query = f"""
        SELECT
            emp_id,
            full_name,
            email
        FROM {EMPLOYEES_TABLE}
        WHERE emp_id = ?
    """

    employee = run_query(
        employee_query,
        (EMPLOYEE_ID,)
    )

    if not employee:
        return json.dumps({
            "success": False,
            "message": "Employee record not found.",
        })

    employee = employee[0]

    # Generate unique ticket ID

    ticket_id = (
        f"HR-{datetime.now().year}-"
        f"{uuid.uuid4().hex[:6].upper()}"
    )

    # Insert ticket into Databricks table

    insert_query = f"""
        INSERT INTO {TICKETS_TABLE} (
            ticket_id,
            emp_id,
            employee_name,
            employee_email,
            category,
            subject,
            description,
            priority,
            status,
            created_at,
            email_status
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            'Open',
            current_timestamp(),
            'Not Sent'
        )
    """

    parameters = (
        ticket_id,
        employee["emp_id"],
        employee["full_name"],
        employee["email"],
        category,
        subject,
        description,
        priority,
    )

    run_query(
        insert_query,
        parameters
    )

    return json.dumps({
        "success": True,
        "ticket_id": ticket_id,
        "employee_name": employee["full_name"],
        "category": category,
        "subject": subject,
        "priority": priority,
        "status": "Open",
        "message": "HR support ticket created successfully.",
    })


# ---------------------------------------------------------
# 8. DATABRICKS AI SEARCH CONFIGURATION
# ---------------------------------------------------------

embedding_model = DatabricksEmbeddings(
    endpoint=EMBEDDING_ENDPOINT
)


# ---------------------------------------------------------
# 9. HR POLICY RETRIEVAL TOOL
# ---------------------------------------------------------

hr_policy_tool = VectorSearchRetrieverTool(
    index_name=VECTOR_SEARCH_INDEX,
    embedding=embedding_model,
    text_column="chunk_text",
    columns=[
        "chunk_id",
        "doc_name",
        "chunk_text",
    ],
    num_results=3,
    query_type="HYBRID",
    tool_name="search_hr_policies",
    tool_description=(
        "Search official HR policy documents to answer "
        "questions about leave policies, eligibility, "
        "carry-forward rules, holidays, employee benefits, "
        "and HR procedures. Use retrieved policy content "
        "as the source of truth."
    ),
    workspace_client=workspace_client,
)


# ---------------------------------------------------------
# 10. DATABRICKS CHAT MODEL
# ---------------------------------------------------------

llm = ChatDatabricks(
    endpoint=LLM_ENDPOINT,
    temperature=0,
)


# ---------------------------------------------------------
# 11. SYSTEM PROMPT
# ---------------------------------------------------------

SYSTEM_PROMPT = """
You are PeopleOps HR Assistant for Nimbus Analytics.

Your responsibility is to answer employee HR questions accurately.

AVAILABLE TOOLS:

1. employee_details_tool
   Retrieves employee profile information.

2. leave_balance_tool
   Retrieves employee-specific leave balances.

3. search_hr_policies
   Searches official HR policy documents.

4. create_hr_ticket
   Creates an HR support ticket when a question cannot
   be resolved using the available information.

ANSWERING RULES:

- Use SQL tools for employee-specific information.
- Use HR policy search for policy-related questions.
- Prefer Leave_Policy_2026 over superseded policies.
- Never invent employee details, leave balances or policies.
- Never invent approval procedures, exception rules,
  manager recommendations or HR workflows.
- If a policy document does not specify a procedure,
  explicitly state that the procedure is not documented.
- Do not present assumptions as official company policy.
- Do not invent contact details or portal URLs.
- Do not promise an HR response time or follow-up
  unless a confirmed process exists.


CONVERSATION AND CONFIRMATION RULES:

- Maintain the context of the entire conversation.
- When a ticket has been proposed, retain its category,
  subject, description and priority.
- A short reply such as "Yes", "Yes please", or
  "Create it" must be interpreted in the context
  of the pending ticket.
- When explicit confirmation is received for a pending
  ticket, immediately call create_hr_ticket.
- Reuse the previously proposed ticket details.
- Never ask the employee to repeat their original question.
- Never ask the employee to provide category, subject,
  description or priority.
- Never ask for confirmation a second time for the
  same pending ticket.
- If the employee declines, do not create the ticket.
- If there is no pending ticket, do not interpret
  an isolated "Yes" as permission to create one.
- After successful creation, return the actual ticket ID.


TICKET CREATION RULES:

1. Never create an HR support ticket without explicit
   employee confirmation.

2. First, attempt to resolve the employee's question
   using the available SQL and HR policy tools.

3. If the question remains unresolved:
   - Determine the appropriate ticket category.
   - Generate a concise and meaningful subject.
   - Generate a detailed description using the employee's
     original question and relevant conversation context.
   - Assign an appropriate priority.
   - Do not ask the employee to provide these details.

4. Present the proposed ticket details:
   - Category
   - Subject
   - Description
   - Priority

5. Ask only:
   "Would you like me to create this HR support ticket?"

6. WAIT for explicit confirmation before calling
   create_hr_ticket.

7. When the employee confirms:
   - Reuse the previously generated ticket details.
   - Do not ask for the category, subject or description again.
   - Do not ask the employee to repeat their original question.
   - Call create_hr_ticket exactly once.

8. If the employee declines:
   - Do not call create_hr_ticket.
   - Politely acknowledge the decision.

9. If the employee requests changes to the proposed ticket,
   update the relevant details and request confirmation again.

10. Never interpret an unrelated message or ambiguous response
    as confirmation.

11. After successful creation, display the ticket ID,
    category, subject and status.

12. Never claim that a ticket was created unless the tool
    confirms successful creation.



RESPONSE RULES:

- Be professional and concise.
- Use clear formatting.
- Never claim that an issue has been escalated unless
  the ticket tool confirms successful creation.
"""


# ---------------------------------------------------------
# 12. LANGGRAPH AGENT
# ---------------------------------------------------------

peopleops_agent = create_agent(
    model=llm,
    tools=[
        employee_details_tool,
        leave_balance_tool,
        hr_policy_tool,
        create_hr_ticket,
    ],
    system_prompt=SYSTEM_PROMPT,
)

# ---------------------------------------------------------
# 13. REUSABLE QUESTION FUNCTION
# ---------------------------------------------------------

def ask_peopleops(
    question: str,
    conversation_history: list = None
) -> str:
    """
    Submit an employee question to the PeopleOps agent
    while preserving previous conversation context.
    """

    messages = []

    # Add previous conversation messages

    for message in conversation_history or []:

        role = message.get("role")

        content = message.get("content", "")

        if role in ["user", "assistant"] and content:

            messages.append(
                (role, content)
            )

    # Add the latest employee question

    messages.append(
        ("user", question.strip())
    )

    # Invoke the agent with conversation history

    response = peopleops_agent.invoke({
        "messages": messages
    })

    return response["messages"][-1].content