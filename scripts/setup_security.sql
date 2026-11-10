-- 1. Create a dedicated schema for our clean AI views
CREATE SCHEMA FDE_VIEWS;
GO 

-- 2. Create the Semantic View (Translating legacy junk to clean English).
--    Columns match what scripts/ingest_legacy_data.py actually loads (the old view referenced
--    DELAY_PROB_DEC / PRT_CNG_LVL / RT_RSK_IDX, which do not exist in the dataset).
CREATE VIEW FDE_VIEWS.VW_ACTIVE_FLEET AS
SELECT 
    VEH_ID AS [Vehicle_ID],
    CARGO_TYPE_TXT AS [Cargo_Type],
    TS_UTC AS [Timestamp],
    V_LAT AS [Latitude],
    V_LON AS [Longitude],
    CAST(IOT_TEMP_VAL_C AS FLOAT) AS [Current_Temperature_C],
    CAST(MIN_TEMP_VAL_C AS FLOAT) AS [Min_Safe_Temp_C],
    CAST(MAX_TEMP_VAL_C AS FLOAT) AS [Max_Safe_Temp_C],
    CGO_COND_CD AS [Cargo_Condition_Code],
    EXCURSION_SEV_TXT AS [Excursion_Severity],
    RISK_CLS_LEV AS [Risk_Classification],
    DELAY_MIN AS [Delay_Minutes]
FROM dbo.TBL_SC_FLEET_HIST_RAW;
GO

-- 3. Create a strict Read-Only Login and User for the AI Agent
CREATE LOGIN USR_FDE_RO WITH PASSWORD = 'AgentPassword2026!';
CREATE USER USR_FDE_RO FOR LOGIN USR_FDE_RO;
GO

-- 4. Grant access ONLY to the semantic view, explicitly denying everything else
GRANT SELECT ON FDE_VIEWS.VW_ACTIVE_FLEET TO USR_FDE_RO;
DENY SELECT ON dbo.TBL_SC_FLEET_HIST_RAW TO USR_FDE_RO;
DENY INSERT, UPDATE, DELETE, ALTER ON SCHEMA::dbo TO USR_FDE_RO;
GO