# Databricks notebook source
# MAGIC %md
# MAGIC ### Connect your existing AI Search index to Python

# COMMAND ----------

# MAGIC %pip install --upgrade databricks-langchain

# COMMAND ----------

dbutils.library.restartPython()

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

result = hr_policy_tool.invoke(
    "What are the holidays in Bengaluru for 2026?"
)

print(result)

# COMMAND ----------

result = hr_policy_tool.invoke(
    "Can employees carry forward their unused leaves?"
)

print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Connect the HR retriever to GPT OSS 120B

# COMMAND ----------

# MAGIC %md
# MAGIC #### Confirm your GPT OSS 120B endpoint name

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

for endpoint in w.serving_endpoints.list():
    if "gpt" in endpoint.name.lower() or "oss" in endpoint.name.lower():
        print(endpoint.name, endpoint.state)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Install LangGraph

# COMMAND ----------

# MAGIC %pip install --upgrade databricks-langchain langgraph

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC #### Build the agent

# COMMAND ----------

# MAGIC %pip install --upgrade "langgraph>=1.1.5" "langgraph-prebuilt>=1.0.9"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent

llm = ChatDatabricks(
    endpoint="databricks-gpt-oss-120b"
)

hr_agent = create_react_agent(
    model=llm,
    tools=[hr_policy_tool],
    prompt="""
    You are the PeopleOps HR Assistant for Nimbus Analytics.

    Answer employee questions using the HR policy search tool
    whenever the question requires information from HR documents.

    Rules:
    1. Use retrieved HR documents as the source of truth.
    2. Do not invent policies, dates, or leave rules.
    3. If the retrieved documents do not contain the answer,
       clearly say that the information was not found.
    4. Give clear, concise answers.
    5. Do not answer employee-specific leave balances yet;
       that SQL tool will be integrated in a later stage.
    """
)

print("PeopleOps HR agent initialized!")

# COMMAND ----------

# MAGIC %md
# MAGIC #### Test the Agent

# COMMAND ----------

response = hr_agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "What are the holidays in Bengaluru for 2026?"
        }
    ]
})

print(response["messages"][-1].content)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Validate policy retrieval

# COMMAND ----------

test_questions = [
    "What is the company policy on accepting gifts?",
    "Can employees carry forward unused leaves?"
]

for q in test_questions:
    print("\nQUESTION:", q)

    response = hr_agent.invoke({
        "messages": [{"role": "user", "content": q}]
    })

    print("ANSWER:", response["messages"][-1].content)