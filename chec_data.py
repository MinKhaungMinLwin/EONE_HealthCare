import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
driver = '{ODBC Driver 18 for SQL Server}'
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;'

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=== CHECKING DATES IN H1OPDIN_TRG ===")
    # Get 5 sample dates
    cursor.execute("SELECT TOP 5 CLINIC_YMD FROM H1OPDIN_TRG ORDER BY CLINIC_YMD DESC")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Sample Date: '{row[0]}' (Type: {type(row[0])})")
        
    print("\n=== CHECKING DATES IN H1ADMINPTNTGB ===")
    cursor.execute("SELECT TOP 5 ADM_YMD FROM H1ADMINPTNTGB ORDER BY ADM_YMD DESC")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Sample Date: '{row[0]}'")

    conn.close()
except Exception as e:
    print(f"Error: {e}")