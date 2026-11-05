# Databricks notebook source
# MAGIC %md
# MAGIC ### Chunk doc_content into smaller chunks
# MAGIC Source table is: `peopleopsproject.genai_book.hr_docs`
# MAGIC
# MAGIC Columns:
# MAGIC - doc_name
# MAGIC - doc_content

# COMMAND ----------

from pyspark.sql.functions import (
    col, explode, monotonically_increasing_id
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType
)

# Read HR documents
hr_df = spark.table(
    "peopleopsproject.genai_book.hr_docs"
)

# Chunking function
def chunk_text(text, chunk_size=700, overlap=100):

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


# Register UDF
from pyspark.sql.functions import udf

chunk_udf = udf(
    chunk_text,
    "array<string>"
)

# Generate chunks
chunked_df = (
    hr_df
    .withColumn(
        "chunks",
        chunk_udf(col("doc_content"))
    )
    .select(
        col("doc_name"),
        explode(col("chunks")).alias("chunk_text")
    )
    .withColumn(
        "chunk_id",
        monotonically_increasing_id()
    )
)

display(chunked_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Save chunked data into a Delta table

# COMMAND ----------

chunked_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(
        "peopleopsproject.genai_book.hr_docs_chunks"
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ### Generate embeddings

# COMMAND ----------

import requests
import pandas as pd

# Databricks workspace configuration
workspace_url = "https://adb-7405605646072267.7.azuredatabricks.net/"
token = dbutils.notebook.entry_point.getDbutils() \
    .notebook().getContext().apiToken().get()

endpoint_name = "databricks-gte-large-en"

url = f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def generate_embeddings(text):

    payload = {
        "input": [text]
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    response.raise_for_status()

    return response.json()["data"][0]["embedding"]

# Read chunked table
chunks_df = spark.table(
    "peopleopsproject.genai_book.hr_docs_chunks"
)

# Convert to Pandas for a small initial dataset
pdf = chunks_df.toPandas()

# Generate embeddings
pdf["embedding"] = pdf["chunk_text"].apply(
    generate_embeddings
)

# Convert back to Spark DataFrame
embedded_df = spark.createDataFrame(pdf)

display(embedded_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Save embeddings into Delta table

# COMMAND ----------

embedded_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(
        "peopleopsproject.genai_book.hr_docs_embeddings"
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ### Enable Change Data Feed
# MAGIC Because we're now using Delta Sync, enable CDF on the embedding table:

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE peopleopsproject.genai_book.hr_docs_embeddings
# MAGIC SET TBLPROPERTIES (
# MAGIC     delta.enableChangeDataFeed = true
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC