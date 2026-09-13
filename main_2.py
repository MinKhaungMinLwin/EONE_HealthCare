import os
import re
from typing import List, Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlalchemy
from sqlalchemy import create_engine, text
from openai import OpenAI
from dotenv import load_dotenv
from sql_templates import SQL_TEMPLATES


# Load environment variables
load_dotenv()

# === Configuration ===
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# === Database Connection ===
driver = 'ODBC Driver 18 for SQL Server'
connection_url = sqlalchemy.engine.URL.create(
    "mssql+pyodbc",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_SERVER,
    database=DB_NAME,
    query={"driver": driver, "TrustServerCertificate": "yes", "Connection Timeout": "30"}
)

engine = None
try:
    engine = create_engine(connection_url)
    with engine.connect() as connection:
         print("Successfully connected to MSSQL Database!")
except Exception as e:
    print(f"CRITICAL ERROR: Database Connection Failed. {e}")

# === FULL SCHEMA FOR Q1-Q11 ===
DB_SCHEMA_CONTEXT = """
**TABLES & JOIN KEYS:**

1. **H1OPD_PTNT_DAILY_DETAIL** (Outpatient Visits)
   - `CLINIC_YMD` (String 'YYYYMMDD'): Visit Date.
   - `DEPT_CD` (String): Department (IM, GS, etc).
   - `CHOJAE_GB` (String): '1'=New Patient, '2'=Return.
   - `INS_GB` (String): '1'=Health Ins, '2'=Car(자보), '3'=Indus(산재).
   - `RCPT_STAT` (String): '9'=No Show(부도), '1'=Normal.
   - `PTNT_NO`: Patient ID.
   - `EMPL_NO`: Doctor ID.

2. **H1ADMINPTNTGB** (Inpatient Admissions)
   - `ADM_YMD` (String 'YYYYMMDD'): Admission Date.
   - `WARD_CD` (String): Ward Code.
   - `PTNT_NO`: Patient ID.

3. **H1PTNT_INFO** (Patient Demographics)
   - `PTNT_NO`: Join Key.
   - `ADDR_1`: Region (Address).
   - `AGE`: Age.
   - `GENDER_CD`: 'M' or 'F'.

4. **NAEUN_EMP** (Doctors)
   - `EMPL_NO`: Join Key.
   - `EMPL_NM`: Doctor Name.
   - `DEPT_CD`: Department.

5. **HZROOM_MASTER** (Hospital Beds)
   - `WARD_CD`: Join Key.
   - `BED_CNT`: Total Bed Capacity.

**MAPPING HINTS:**
- **Region (Q10):** JOIN `H1OPD_PTNT_DAILY_DETAIL` with `H1PTNT_INFO` on `PTNT_NO`.
- **Beds (Q9):** JOIN `H1ADMINPTNTGB` with `HZROOM_MASTER` on `WARD_CD`.
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

# === STRICT PROMPTS ===

SYSTEM_PROMPT_SQL = f"""
You are a STRICT Microsoft SQL Server (T-SQL) query generator.

════════════════════════════════
DATABASE DIALECT (ABSOLUTE)
════════════════════════════════
- Database: Microsoft SQL Server
- ❌ MySQL / PostgreSQL functions are FORBIDDEN:
  DATE_FORMAT, CURDATE, DATE_SUB, NOW, LIMIT, IFNULL
- ✅ Allowed:
  LEFT(), COUNT(), SUM(CASE WHEN...), GROUP BY, ORDER BY

════════════════════════════════
CORE RULES (NO EXCEPTIONS)
════════════════════════════════
1. ❌ NO MATH in SQL
   - Do NOT calculate ratios, percentages, growth, or division
   - ONLY return RAW COUNTS

2. ❌ NO DATE FILTERING
   - Do NOT use WHERE date = today / last month
   - ALWAYS return multiple months using GROUP BY

3. ❌ NO SUBQUERIES / CTEs / WINDOW FUNCTIONS
   - Single SELECT
   - Simple JOINs only

4. ✅ MONTH GROUPING STANDARD
   - ALL date columns are STRING 'YYYYMMDD'
   - ALWAYS group by: LEFT(date_column, 6) AS YM

5. ✅ ALIAS RULE (SQL Server)
   - DO NOT use SELECT alias in GROUP BY or ORDER BY
   - Repeat the FULL expression

6. ❌ NO NATURAL LANGUAGE
   - OUTPUT SQL ONLY
   - No explanation
   - No markdown

════════════════════════════════
SCHEMA (AUTHORITATIVE)
════════════════════════════════
{DB_SCHEMA_CONTEXT}

════════════════════════════════
QUESTION → SQL BEHAVIOR
════════════════════════════════
- Trend / comparison → GROUP BY month
- Ratio / percentage → return numerator & denominator only
- Prediction → SQL NEVER predicts (LLM will)

If unsure, RETURN MORE DATA (counts by month).
"""

SYSTEM_PROMPT_ANALYSIS = """
You are a Medical AI Analyst.
You receive: User Question, SQL Used, and Raw Data.

**YOUR RESPONSIBILITY:**
The SQL only gives you RAW numbers. **YOU** must do the math.

1. **Calculate Ratios:** 
   - If SQL returns: `New: 50, Return: 150`.
   - YOU write: "New patients are 50, Returning are 150. The Ratio is 1:3 (25% New)."
2. **Compare Trends:**
   - Compare the rows (Month vs Month).
   - "Patients decreased from 100 in Jan to 80 in Feb."
3. **Specifics:**
   - **Q7 (Car/Indus):** Identify which insurance type is lower. Suggest marketing.
   - **Q9 (Beds):** If Occupancy (Count/Capacity) is low, suggest "Specialized Centers".
   - **Q10 (Region):** Identify the top region. Suggest "Local Community Outreach".

**LANGUAGE RULE (CRITICAL):**
- You must output in the language of the User Question.
- IF the question is in Korean, respond completely in Korean.
- IF the question is in English, respond completely in English.

**ERROR HANDLING:**
- If Raw Data is `[]`, say "데이터가 없습니다 (No Data)."
"""

SYSTEM_PROMPT_CHAT = """
You are a helpful Medical AI Assistant.
You can help users with general questions or greet them.

**LANGUAGE RULES (STRICT):**
1. **User speaks Korean** -> You answer in **Korean**.
2. **User speaks English** -> You answer in **English**.
3. Keep answers concise and polite.
"""

# === FUNCTIONS ===

def resolve_intent(question: str):
    for qid, cfg in SQL_TEMPLATES.items():
        if any(k in question for k in cfg["keywords"]):
            return qid, cfg["sql"]
    return None, None

def is_sql_intent(text: str) -> bool:
    sql_keywords = [
        "환자", "신환", "재진", "과별", "진료과", "입원",
        "보험", "병상", "추이", "통계", "비율",
        "patient", "department", "trend", "count", "ratio"
    ]
    t = text.lower()
    return any(k in t for k in sql_keywords)


def clean_sql(text: str) -> str:
    """Removes text, leaving only SQL."""
    text = text.replace("```sql", "").replace("```", "").strip()
    match = re.search(r"(SELECT[\s\S]+)", text, re.IGNORECASE)
    if match: return match.group(1)
    return text

def get_schema_info(tables: List[str]) -> str:
    """Fallback to get real columns if hallucination occurs."""
    if not tables or engine is None: return ""
    try:
        clean = [re.sub(r'[^a-zA-Z0-9_]', '', t) for t in tables]
        fmt = "', '".join(clean)
        with engine.connect() as c:
            q = f"SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ('{fmt}')"
            rows = c.execute(text(q)).fetchall()
            return str(rows)
    except: return ""

def fix_sql(question: str, bad_sql: str, error: str) -> str:
    """Self-Correction Agent."""
    schema = get_schema_info(re.findall(r'\b(?:FROM|JOIN)\s+([A-Za-z0-9_]+)', bad_sql, re.IGNORECASE))
    
    prompt = f"""
    Fix this SQL.
    Error: {error}
    Bad SQL: {bad_sql}
    Schema Columns: {schema}
    
    **RULES:**
    1. **REMOVE MATH:** No division (`/`). Just select RAW COUNTS.
    2. **REMOVE DATE FILTERS:** Remove `WHERE Date > ...`. Just use `ORDER BY Date DESC`.
    3. **CHECK COLUMNS:** Use the Schema Columns provided above.
    4. **OUTPUT SQL ONLY.**
    """
    resp = client.chat.completions.create(model="solar-1-mini-chat", messages=[{"role":"user", "content":prompt}])
    return clean_sql(resp.choices[0].message.content)

def generate_sql(question: str) -> str:
    resp = client.chat.completions.create(
        model="solar-1-mini-chat",
        messages=[{"role": "system", "content": SYSTEM_PROMPT_SQL}, {"role": "user", "content": question}],
        temperature=0
    )
    return clean_sql(resp.choices[0].message.content)

def run_query(sql: str) -> Union[List[dict], str]:
    if engine is None: return "DB Not Connected"
    try:
        with engine.connect() as c:
            result = c.execute(text(sql))
            rows = [dict(r._mapping) for r in result]
            if len(rows) > 50: return rows[:50]
            return rows
    except Exception as e: return f"SQL Error: {e}"

def analyze(question: str, data: any, sql: str) -> str:
    has_korean = re.search(r"[가-힣]", question)

    if has_korean:
        target_lang = "Korean"
        lang_instruction = "IMPORTANT: The user asked in Korean. You must answer in Korean."
    else:
        target_lang = "English"
        lang_instruction = "IMPORTANT: The user asked in English. You must answer in English."

    context = f"""
    Q: {question}
    Target Language: {target_lang}
    SQL: {sql}
    Data: {data}
    {lang_instruction}
    """

    resp = client.chat.completions.create(
        model="solar-1-mini-chat",
        messages=[{"role": "system", "content": SYSTEM_PROMPT_ANALYSIS}, {"role": "user", "content": context}]
    )
    return resp.choices[0].message.content

# === ENDPOINT ===

@app.post("/chat")
async def chat(request: ChatRequest):
    q = request.messages[-1].content

    # 1. Check Language (for strict instruction)
    has_korean = re.search(r"[가-힣]", q)
    if has_korean:
        lang_instruction = "User asked in Korean. You must answer in Korean."
    else:
        lang_instruction = "User asked in English. You must answer in English."

    # 2. Try to find a matching SQL Template
    qid, sql = resolve_intent(q)

    # =====================================================
    # SCENARIO A: It IS a Database Question (SQL Found)
    # =====================================================
    if sql:
        data = run_query(sql)

        # Handle DB Errors
        if isinstance(data, str):
            # If DB fails, apologize in the correct language
            if has_korean:
                return {"role": "assistant", "content": f"데이터 조회 중 오류가 발생했습니다: {data}"}
            else:
                return {"role": "assistant", "content": f"An error occurred while fetching data: {data}"}
            
        # Analyze Data (This function already handles language logic from previous step)
        ans = analyze(q, data, sql)
        return {"role": "assistant", "content": ans}
    
    # =====================================================
    # SCENARIO B: It is NOT a Database Question (Normal Chat)
    # =====================================================
    else:
        # Instead of returning "Not Supported", handle as normal chat with LLM
        resp = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_CHAT + "\n" + lang_instruction},
                {"role": "user", "content": f"{q}"}
            ]
        )
        return {"role": "assistant", "content": resp.choices[0].message.content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)