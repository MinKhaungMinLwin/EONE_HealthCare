import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

# Database Connection Details
server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

conn_str = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server={server};"
    f"Database={database};"
    f"UID={username};"
    f"PWD={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("Successfully connected to MSSQL Database!")

    query = """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_NAME;
    """

    cursor.execute(query)
    tables = cursor.fetchall()

    print(f"--- Database Schema for {database} ---")

    print("Tables Names:")
    for row in tables:
        print(f"- {row.TABLE_NAME}")
    print(f"Total Tables Found: {len(tables)}\n")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error connecting to database: {e}")