import pandas as pd
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "diabetes+130-us+hospitals+for+years+1999-2008"

csv_data_path = RAW_DATA_DIR / "diabetic_data.csv"
csv_mapping_path = RAW_DATA_DIR / "IDS_mapping.csv"
db_output_path = PROJECT_ROOT / "data" / "diabetes_hospital.db"

# Load CSV files into pandas DataFrames
print("Loading CSV files...")
df = pd.read_csv(csv_data_path)
mapping = pd.read_csv(csv_mapping_path)

# Create a connection to the SQLite database
# This will automatically create the .db file if it does not exist
print("Creating SQLite database...")
conn = sqlite3.connect(db_output_path)

# Transfer the data from the DataFrames into SQLite tables
# 'encounters' will hold patient data, 'id_mappings' will hold the dictionary codes
print("Writing data to database tables...")
df.to_sql('encounters', conn, if_exists='replace', index=False)
mapping.to_sql('id_mappings', conn, if_exists='replace', index=False)

# Close the database connection
conn.close()
print(f"Success! Database created at: {db_output_path}")
