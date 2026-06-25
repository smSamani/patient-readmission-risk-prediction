-- Master Tableau Dataset Query
-- Purpose:
-- Create a row-level BI dataset for Tableau dashboarding.
-- Each row represents one hospital encounter.
-- This query keeps raw granularity while adding business-friendly engineered fields.

SELECT
    encounter_id,
    patient_nbr,
    age,
    gender,
    race,

    admission_type_id,
    discharge_disposition_id,
    admission_source_id,

    time_in_hospital,
    num_lab_procedures,
    num_procedures,
    num_medications,
    number_outpatient,
    number_emergency,
    number_inpatient,
    number_diagnoses,

    A1Cresult,

    CASE
        WHEN A1Cresult IS NULL THEN 'Not Tested'
        ELSE 'Tested'
    END AS a1c_test_status,

    diag_1,
    diag_2,
    diag_3,

CASE

    -- Diabetes
    WHEN diag_1 LIKE '250%' THEN 'Diabetes'

    -- Circulatory System
    WHEN CAST(diag_1 AS REAL) BETWEEN 390 AND 459 THEN 'Circulatory'

    -- Respiratory System
    WHEN CAST(diag_1 AS REAL) BETWEEN 460 AND 519 THEN 'Respiratory'

    -- Digestive System
    WHEN CAST(diag_1 AS REAL) BETWEEN 520 AND 579 THEN 'Digestive'

    -- Genitourinary System
    WHEN CAST(diag_1 AS REAL) BETWEEN 580 AND 629 THEN 'Genitourinary'

    -- Musculoskeletal System
    WHEN CAST(diag_1 AS REAL) BETWEEN 710 AND 739 THEN 'Musculoskeletal'

    -- Symptoms & Ill-defined Conditions
    WHEN CAST(diag_1 AS REAL) BETWEEN 780 AND 799 THEN 'Symptoms'

    -- Injury & Poisoning
    WHEN CAST(diag_1 AS REAL) BETWEEN 800 AND 999 THEN 'Injury'

    -- Infectious Diseases
    WHEN CAST(diag_1 AS REAL) BETWEEN 1 AND 139 THEN 'Infectious'

    -- Neoplasms
    WHEN CAST(diag_1 AS REAL) BETWEEN 140 AND 239 THEN 'Neoplasms'

    -- Endocrine / Metabolic
    WHEN CAST(diag_1 AS REAL) BETWEEN 240 AND 279 THEN 'Endocrine/Metabolic'

    ELSE 'Other'

END AS diag_1_group,

    readmitted,

    CASE
        WHEN readmitted = '<30' THEN 1
        ELSE 0
    END AS is_readmitted_30,

    CASE
        WHEN readmitted = '<30' THEN 15200
        ELSE 0
    END AS penalty_cost

FROM encounters;