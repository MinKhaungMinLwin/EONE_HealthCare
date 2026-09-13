SQL_TEMPLATES = {

    "Q1": {
        "description": "신규 환자 대 재진 환자 비율",
        "keywords": [
            "신환", "재진", "신환대비",
            "전월", "저번달"
        ],
        "sql": """
        SELECT TOP 12
            CONVERT(VARCHAR(6), CLINIC_YMD, 112) AS Month,
            -- Code 10 is NEW
            SUM(CASE WHEN CHOJAE_GB = '10' THEN 1 ELSE 0 END) AS NewCnt,
            -- Codes 20 and 30 are RETURN
            SUM(CASE WHEN CHOJAE_GB IN ('20', '30') THEN 1 ELSE 0 END) AS ReturnCnt
        FROM H1OPDIN_TRG
        GROUP BY CONVERT(VARCHAR(6), CLINIC_YMD, 112)
        ORDER BY Month DESC
        """
    },

    "Q2": {
        "description": "월별 재원 환자 수 추이 (Inpatient Census Trend)",
        "keywords": [
            "입원", "재원", "입원환자", "재원환자",
            "병동", "병상", "inpatient", "census", "추이"
        ],
        "sql": """
        SELECT
            M.YM AS Month,
            COUNT(DISTINCT A.RECEPT_NO) AS InpatientCnt
        FROM
        (
            SELECT DISTINCT
                LEFT(ADM_YMD, 6) AS YM
            FROM H1ADMINPTNTGB
        ) M
        JOIN H1ADMINPTNTGB A
            ON A.ADM_YMD <= M.YM + '31'
        AND (A.DCHG_YMD IS NULL OR A.DCHG_YMD >= M.YM + '01')
        GROUP BY M.YM
        ORDER BY M.YM DESC
        """
    },

    "Q3": {
        "description": "특정 의사 환자수 (Doctor Trend)",
        "keywords": [
            "의사", "의사별", "의사환자수",
            "교수", "담당의", "doctor", "Dr"
        ],
        "sql": """
        SELECT TOP 20
            O.CLINIC_YMD,
            O.DOCT_EMPL_NO,
            E.EMPL_NM
        FROM H1OPDIN_TRG O
        JOIN HZEMPL E ON O.DOCT_EMPL_NO = E.EMPL_NO;
        """
    },

    "Q4": {
        "description": "과별 환자수 (Dept Trend)",
        "keywords": [
            "과별", "진료과", "부서", "과",
            "department", "dept", "환자수"
        ],
        "sql": """
        SELECT TOP 50
            CONVERT(VARCHAR(6), A.CLINIC_YMD, 112) AS Month,
            A.DEPT_CD,
            
            -- 1. GENDER
            ISNULL(B.SEX, 'Unknown') AS Gender,
            
            -- 2. AGE GROUP (Calculated: (ThisYear - BirthYear) -> Group by 10s)
            CASE 
                -- Safety check for empty or invalid birth dates
                WHEN B.BIRTH_YMD IS NULL OR ISNUMERIC(LEFT(B.BIRTH_YMD, 4)) = 0 THEN 'Unknown'
                ELSE CAST(((YEAR(GETDATE()) - CAST(LEFT(B.BIRTH_YMD, 4) AS INT)) / 10 * 10) AS VARCHAR) + 's'
            END AS AgeGroup,

            COUNT(*) AS PatientCnt

        FROM H1OPDIN_TRG A
        -- Join using the confirmed column PTNT_NO
        LEFT JOIN H1PTNT_INFO B ON A.PTNT_NO = B.PTNT_NO

        GROUP BY 
            CONVERT(VARCHAR(6), A.CLINIC_YMD, 112), 
            A.DEPT_CD, 
            B.SEX,
            CASE 
                WHEN B.BIRTH_YMD IS NULL OR ISNUMERIC(LEFT(B.BIRTH_YMD, 4)) = 0 THEN 'Unknown'
                ELSE CAST(((YEAR(GETDATE()) - CAST(LEFT(B.BIRTH_YMD, 4) AS INT)) / 10 * 10) AS VARCHAR) + 's'
            END

        ORDER BY Month DESC, PatientCnt DESC
        """
    },
    "Q5": {
        "description": "환자수 증감이 적은 과 + 환자수가 적은 과",
        "keywords": [
            "증감", "증가", "감소",
            "제일 낮은", "가장 적은",
            "환자수", "과", "진료과",
            "변화", "추이"
        ],
        "sql": """
        SELECT
            CONVERT(VARCHAR(6), CLINIC_YMD, 112) AS Month,
            DEPT_CD,
            COUNT(*) AS PatientCnt
        FROM H1OPDIN_TRG
        GROUP BY CONVERT(VARCHAR(6), CLINIC_YMD, 112), DEPT_CD
        ORDER BY Month DESC
        """
    },
    "Q6": {
        "description": "과별 성별/나이 분포 (Demographics)",
        "keywords": [
            "성별", "연령", "나이", "연령대",
            "분포", "demographic", "age", "gender"
        ],
        "sql": """
        SELECT TOP 50
            O.DEPT_CD,
            P.SEX AS Gender,
            CASE 
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 10 THEN '0-9'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 20 THEN '10-19'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 30 THEN '20-29'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 40 THEN '30-39'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 50 THEN '40-49'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 60 THEN '50-59'
                ELSE '60+' 
            END AS AgeGroup,
            COUNT(*) AS PatientCnt
        FROM H1OPDIN_TRG O
        JOIN H1PTNT_INFO P 
            ON O.PTNT_NO = P.PTNT_NO
        GROUP BY 
            O.DEPT_CD,
            P.SEX,
            CASE 
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 10 THEN '0-9'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 20 THEN '10-19'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 30 THEN '20-29'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 40 THEN '30-39'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 50 THEN '40-49'
                WHEN DATEDIFF(YEAR, P.BIRTH_YMD, GETDATE()) < 60 THEN '50-59'
                ELSE '60+' 
            END
        ORDER BY O.DEPT_CD;
        """
    },
    "Q7": {
        "description": "보험 유형별 (Insurance)",
        "keywords": [
            "보험", "보험유형", "보험별",
            "건강보험", "산재", "자보", "insurance"
        ],
        "sql": """
        SELECT
            CASE 
                WHEN SAN_GB = 'Y' THEN 'Industrial Accident (산재)'
                WHEN INSR_TYPE = '2' THEN 'Car Insurance (자보)'
                WHEN INSR_TYPE = '1' THEN 'Health Insurance'
                ELSE 'Other'
            END AS InsuranceType,
            CASE 
                WHEN VISIT_GB = 'O' THEN 'Outpatient'
                WHEN VISIT_GB = 'I' THEN 'Inpatient'
                ELSE 'Other'
            END AS VisitType,
            COUNT(*) AS PatientCnt
        FROM H1OPDIN_TRG
        GROUP BY
            CASE 
                WHEN SAN_GB = 'Y' THEN 'Industrial Accident (산재)'
                WHEN INSR_TYPE = '2' THEN 'Car Insurance (자보)'
                WHEN INSR_TYPE = '1' THEN 'Health Insurance'
                ELSE 'Other'
            END,
            CASE 
                WHEN VISIT_GB = 'O' THEN 'Outpatient'
                WHEN VISIT_GB = 'I' THEN 'Inpatient'
                ELSE 'Other'
            END
        ORDER BY PatientCnt DESC;
        """
    },
    "Q8": {
        "description": "과별 실제 외래 진료 완료 건수",
        "keywords": [
            "외래", "실제진료",
            "내원", "방문",
            "진료완료", "과"
        ],
        "sql": """
        SELECT
            DEPT_CD,
            COUNT(*) AS VisitCompletedCnt
        FROM H1OPDIN_TRG
        WHERE COME_PASS_GB = '10'
        AND VISIT_PASS_GB = '30'
        GROUP BY DEPT_CD
        """
    },
    "Q9": {
        "description": "병상 가동률 (Bed Occupancy)",
        "keywords": [
            "병상", "가동률", "병상가동",
            "ward", "bed", "occupancy"
        ],
        "sql": """
        SELECT
            WARD_CD,
            SUM(TOT_BED_CNT) AS TotalBeds,
            SUM(USE_BED_CNT) AS UsedBeds,
            CAST(
                SUM(USE_BED_CNT) * 100.0 / NULLIF(SUM(TOT_BED_CNT), 0)
                AS DECIMAL(5,2)
            ) AS OccupancyRatePct
        FROM HZROOM_MASTER
        WHERE USE_YN = 'Y'
        GROUP BY WARD_CD
        ORDER BY OccupancyRatePct DESC;
        """
    },

    "Q10": {
        "description": "지역별 신환 (Region)",
        "keywords": [
            "지역", "지역별", "주소",
            "거주지", "신환지역", "region"
        ],
        "sql": """
        SELECT TOP 20
            LEFT(P.ADDR, 2) AS Region,
            COUNT(DISTINCT O.PTNT_NO) AS NewPatientCnt
        FROM H1OPDIN_TRG O
        JOIN H1PTNT_INFO P
            ON O.PTNT_NO = P.PTNT_NO
        WHERE O.CHOJAE_GB = '10'
        AND P.ADDR IS NOT NULL
        GROUP BY LEFT(P.ADDR, 2)
        ORDER BY NewPatientCnt DESC;
        """
    },

    "Q11": {
        "description": "병원 전체 추이 (Total Trend)",
        "keywords": [
            "전체", "전체환자", "병원전체",
            "총환자수", "total", "overall", "추이"
        ],
        "sql": """
        SELECT TOP 12
            CONVERT(VARCHAR(6), CLINIC_YMD, 112) AS Month,
            COUNT(*) AS TotalPatientCnt
        FROM H1OPDIN_TRG
        GROUP BY CONVERT(VARCHAR(6), CLINIC_YMD, 112)
        ORDER BY Month DESC
        """
    }
}
