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

data_path = project_root / "data" / "raw" / "cold_chain_delivery_trips.csv"

db_host = os.getenv("SQL_SERVER_HOST" , "localhost")
db_port = os.getenv("SQL_SERVER_PORT", "1433")
db_user = os.getenv("SQL_ADMIN_USER")
db_password = os.getenv("SQL_ADMIN_PASSWORD")

# 1. Load the raw dataset
print(f"Loading CSV from {data_path}...")
df = pd.read_csv(data_path)

legacy_mapping = {
    # Timestamp
    'Data_Ping_time': 'TS_UTC',

    # Vehicle GPS coordinates
    'Curr_lat': 'V_LAT',
    'Curr_lon': 'V_LON',

    # Temperature telemetry
    'temperature_c': 'IOT_TEMP_VAL_C',
    'min_temp': 'MIN_TEMP_VAL_C',
    'max_temp': 'MAX_TEMP_VAL_C',
    'humidity_percent': 'IOT_HUMIDITY_PCT',

    # Cold-chain condition
    'cold_chain_status': 'CGO_COND_CD',
    'excursion_severity': 'EXCURSION_SEV_TXT',

    # Risk classification
    'risk_level': 'RISK_CLS_LEV',

    # Delivery and delay
    'delay_minutes': 'DELAY_MIN',

    # Route and vehicle information
    'Origin_Location': 'ORG_LOC_TXT',
    'Destination_Location': 'DEST_LOC_TXT',
    'TRANSPORTATION_DISTANCE_IN_KM': 'ROUTE_DIST_KM',

    # Cargo information
    'product_type': 'CARGO_TYPE_TXT',

    # Identifiers
    'vehicle_no': 'VEH_ID'
}

df_legacy = df[list(legacy_mapping.keys())].rename(columns=legacy_mapping)

print(df_legacy.shape)

# 3. Connect to Docker MSSQL Server
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

# 4. Ingest data into the messy table name
table_name = 'TBL_SC_FLEET_HIST_RAW'
print(f"Ingesting into {table_name}. This may take a minute...")
df_legacy.to_sql(table_name, engine, if_exists='replace', index=False, schema='dbo')

print("✅ Legacy data ingestion complete!")