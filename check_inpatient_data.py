import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# Database Connection
server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
driver = '{ODBC Driver 18 for SQL Server}'
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;'

# Candidates for Admission/Inpatient Data
candidates = [
    "H1ADMIN",                   # Common master table name
    "H1ADMIN_HISTORY",           # History table
    "H1ADMINPTNTGB",             # Patient Type breakdown
    "DCM_EXT_IN_PATIENT_DETAIL", # Data Mart table
    "H3NUR_TOTAL_STAY_LIST",     # Nursing Stay List (Current Inpatients)
    "H1ADM_BILL_MASTER_NDRG"     # Billing Master (often reliable for counts)
]

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=== SEARCHING FOR ADMISSION DATA ===")
    
    found_table = None
    
    for table in candidates:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table '{table}': {count} rows")
            
            if count > 0 and found_table is None:
                found_table = table
                
        except Exception as e:
            print(f"Table '{table}': Error accessing ({e})")

    if found_table:
        print(f"\n✅ WINNER: We should use '{found_table}'")
        
        # Check columns
        print(f"\n=== Columns in {found_table} ===")
        cursor.execute(f"SELECT TOP 1 * FROM {found_table}")
        columns = [column[0] for column in cursor.description]
        print(columns)
        
        # Check for Date column
        date_col = next((c for c in columns if 'YMD' in c or 'DATE' in c), "Unknown")
        print(f"\nLikely Date Column: {date_col}")
        
    else:
        print("\n❌ CRITICAL: No admission data found. Please check with your DB admin.")

    conn.close()

except Exception as e:
    print(f"Connection Error: {e}")