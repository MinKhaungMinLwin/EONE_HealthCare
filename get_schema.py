import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# Database Connection Details
server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

driver = '{ODBC Driver 18 for SQL Server}'
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;'

# === CRITICAL CHANGE: REDUCED TABLE LIST ===
# We only select tables necessary for patient flow, admissions, doctors, and insurance.
# This keeps the token count low enough for the AI to handle.
target_tables = [
    # --- Core Patient Info ---
    "H1PTNT_INFO",              # Basic patient demographics (Age, Sex, Address)
    "H1ADMINPTNTGB",            # Patient types/classifications (보험유형 identifiers like 자보, 산재 might be here or linked here)

    # --- Outpatient (외래) ---
    "H1OPD_PTNT_DAILY_DETAIL",  # Daily outpatient visits (Key for Dept stats, new vs returning)
    "H1OPDADM_CLINIC_TOT",      # Outpatient clinic totals

    # --- Inpatient/Admission (입원) ---
    "H1ADM_PTNT_DAILY_DETAIL",  # Daily admission details (Key for length of stay, ward info)
    "H1OPDIN_TRG",              # Admission triggers/requests (might contain initial admission data)
    
    # --- Wards/Beds (병동/병상) ---
    "HZROOM_MASTER",            # Master list of rooms/wards (Crucial for 병상가동율)

    # --- Doctors/Staff (의료진) ---
    "NAEUN_EMP",                # Employee master (Likely contains Doctor names like '홍길동' and their dept codes)
    "H1MEDFEE_MASTER",          # Often contains links between doctors, departments, and fees

    # --- Insurance/Financial Details ---
    "DCM_EXT_INSURANCE_PATIENT_DETAIL", # Detailed insurance info for patients
    "H1ADM_BILL_MASTER_NDRG",   # Billing master (if needed for revenue questions later)
]
# ===========================================

def get_table_schema(connection, table_name):
    cursor = connection.cursor()
    # T-SQL query to get column info
    query = f"""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{table_name}'
    """
    cursor.execute(query) #   ORDER BY ORDINAL_POSITION
    columns = cursor.fetchall()
    
    if not columns:
        return f"TABLE: {table_name} (WARNING: Table not found or no permission)\n\n"

    schema_str = f"TABLE: {table_name}\nColumns:\n"
    for col in columns:
        col_name = col[0]
        data_type = col[1]
        # Only add length for string types to save tokens
        # length = f"({col[2]})" if col[2] and data_type in ['varchar', 'nvarchar', 'char'] else ""
        schema_str += f"  - {col_name} ({data_type})\n"
    schema_str += "---------------------------\n"
    return schema_str

try:
    print("Connecting to Database to fetch schema...")
    conn = pyodbc.connect(conn_str)
    
    full_schema_context = "Here is the database schema for key hospital tables.\n\n"
    print(f"Fetching schema for {len(target_tables)} essential tables...")
    
    for table in target_tables:
        print(f"Processing: {table}")
        full_schema_context += get_table_schema(conn, table)
        # try:
        #     full_schema_context += get_table_schema(conn, table)
        # except Exception as e:
        #     print(f"Error fetching {table}: {e}")

    # Save schema to a file for the chatbot to use
    with open("db_context.txt", "w", encoding="utf-8") as f:
        f.write(full_schema_context)
    
    print("\nSUCCESS! New, smaller schema saved to 'db_context.txt'.")
    # print(f"Preview of context:\n{full_schema_context[:500]}...")
    conn.close()

except Exception as e:
    print(f"\nDatabase Connection Error: {e}")
    print("Ensure credentials in .env are correct and VPN is active.")