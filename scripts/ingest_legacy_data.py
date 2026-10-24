from pathlib import Path
import pandas as pd
import urllib
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# __file__ is 'experiment/phase-0/ingest_legacy_data.py'
script_dir = Path(__file__).resolve().parent # points to experiment/phase-0
project_root = script_dir.parents[0] # climbs up 1 levels to project root

load_dotenv(project_root / ".env")

data_path = project_root / "data" / "Delivery_Logistics.csv"

# db_host = os.getenv("SQL_SERVER_HOST", "localhost")
db_host = "localhost"
db_port = os.getenv("SQL_SERVER_PORT", "1433")
db_user = os.getenv("SQL_ADMIN_USER")
db_password = os.getenv("SQL_ADMIN_PASSWORD")

# 1. Load the raw dataset
print(f"Loading CSV from {data_path}...")
df = pd.read_csv(data_path)

# 2. Connect to Docker MSSQL Server
print("Connecting to legacy MSSQL Database...")
# Use the pyodbc driver. (Ensure you have ODBC Driver 17 or 18 for SQL Server installed on your OS)
connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={db_host},{db_port};"
        f"DATABASE=master;"
        f"UID={db_user};"
        f"PWD={db_password};"
        f"Encrypt=no;"
        f"TrustServerCertificate=yes;"
    )

params = urllib.parse.quote_plus(connection_string)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# 3. Ingest data into the messy table name
table_name = 'TBL_SC_FLEET_HIST_RAW'
print(f"Ingesting into {table_name}. This may take a minute...")
df.to_sql(table_name, engine, if_exists='replace', index=False, schema='dbo')

print("✅ Legacy data ingestion complete!")
