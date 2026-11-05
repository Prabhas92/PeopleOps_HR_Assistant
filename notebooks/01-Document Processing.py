# Databricks notebook source
# MAGIC %md
# MAGIC ### PDF Document Processing Pipeline
# MAGIC **Objective:** Extract text from product documentation PDFs and store in a Unity Catalog table
# MAGIC
# MAGIC **Source Location:** `/Volumes/peopleopsproject/genai_book/hr_docs/`
# MAGIC
# MAGIC **Target Table:** `peopleopsproject.genai_book.hr_docs`
# MAGIC
# MAGIC **Schema:**
# MAGIC - `doc_name` - PDF filename without extension
# MAGIC - `doc_content` - Extracted text content

# COMMAND ----------

# MAGIC  %pip install PyPDF2

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 1: Discover PDF Files
# MAGIC
# MAGIC We'll use `dbutils.fs.ls()` to list all PDF files in the source directory.
# MAGIC

# COMMAND ----------

source_path = "/Volumes/peopleopsproject/genai_book/hr_docs/"
files = dbutils.fs.ls(source_path)

pdf_files = [f for f in files if f.name.endswith('.pdf')]

print(f"Found {len(pdf_files)} PDF files:")
for pdf in pdf_files:
    print(f"  - {pdf.name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 2: Extract Text from Each PDF
# MAGIC
# MAGIC  We'll define a function to:
# MAGIC  1. Read each PDF file using PyPDF2
# MAGIC  2. Extract text from all pages
# MAGIC  3. Return the product name and extracted text
# MAGIC

# COMMAND ----------

import PyPDF2
import io

def extract_text_from_pdf(file_path):
    """
    Extract text content from a PDF file.
    
    Args:
        file_path: Full path to the PDF file in DBFS/Volumes
    
    Returns:
        Extracted text as a string
    """
    try:
        # Read the PDF file content
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes.encode('latin-1') if isinstance(pdf_bytes, str) else pdf_bytes))
        
        # Extract text from all pages
        text_content = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n"
        
        return text_content.strip()
    
    except Exception as e:
        print(f"Error extracting text from {file_path}: {str(e)}")
        return None

print("Text extraction function defined successfully!")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 3: Process All PDF Files
# MAGIC
# MAGIC  Now we'll iterate through each PDF file, extract the text, and prepare the data for our table.

# COMMAND ----------

hr_data = []

# Process each PDF file
for pdf_file in pdf_files:
    print(f"Processing: {pdf_file.name}")
    
    # Extract product name (remove .pdf extension)
    doc_name = pdf_file.name.replace('.pdf', '')
    
    # Extract text from the PDF
    full_path = f"{source_path}{pdf_file.name}"
    hr_doc = extract_text_from_pdf(full_path)
    
    if hr_doc:
        hr_data.append({
            'doc_name': doc_name,
            'hr_doc': hr_doc
        })
        print(f"  ✓ Successfully extracted {len(hr_doc)} characters")
    else:
        print(f"  ✗ Failed to extract text")

print(f"\nTotal documents processed: {len(hr_data)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 4: Create Delta Table
# MAGIC
# MAGIC  We'll:
# MAGIC  1. Convert the extracted data into a Spark DataFrame
# MAGIC  2. Write it to the Unity Catalog table `peopleopsproject.genai_book.hr_docs`
# MAGIC  3. Use `overwrite` mode to replace any existing data
# MAGIC

# COMMAND ----------

# DBTITLE 1,Create Delta table
from pyspark.sql.types import StructType, StructField, StringType

# Define schema for the DataFrame
schema = StructType([
    StructField("doc_name", StringType(), False),
    StructField("doc_content", StringType(), True)
])

# Create Spark DataFrame from the extracted data
df = spark.createDataFrame([(row['doc_name'], row['hr_doc']) for row in hr_data], schema=schema)

# Display the DataFrame schema and count
print(f"DataFrame created with {df.count()} rows\n")
df.printSchema()

# Write to Unity Catalog table
table_name = "peopleopsproject.genai_book.hr_docs"
print(f"\nWriting data to table: {table_name}")

df.write \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(table_name)

print(f"✓ Successfully created table: {table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 5: Verify the Table
# MAGIC
# MAGIC Let's query the table to verify the data was stored correctly.
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from peopleopsproject.genai_book.hr_docs