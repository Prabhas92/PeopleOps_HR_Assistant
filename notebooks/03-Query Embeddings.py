# Databricks notebook source
# MAGIC %pip install databricks-openai

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

for ep in w.serving_endpoints.list():
    if "gte" in ep.name.lower():
        print(ep.name)

# COMMAND ----------

from databricks_openai import DatabricksOpenAI

client = DatabricksOpenAI()

response = w.serving_endpoints.query(
    name="databricks-gte-large-en",
    input="holidays in bengaluru location"
)

query_embedding = response.data[0].embedding

print("Embedding dimension:", len(query_embedding))

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

index = vsc.get_index(
    endpoint_name="peopleops_vs_endpoint",
    index_name="peopleopsproject.genai_book.hr_docs_vs_index_v2"
)

results = index.similarity_search(
    query_vector=query_embedding,
    columns=["doc_name", "chunk_text"],
    num_results=3
)

display(results)