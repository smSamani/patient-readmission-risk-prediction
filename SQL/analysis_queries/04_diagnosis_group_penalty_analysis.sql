-- Diagnosis Group Penalty Analysis

SELECT

    CASE

        -- Diabetes
        WHEN diag_1 LIKE '250%' THEN 'Diabetes'

        -- Circulatory
        WHEN CAST(diag_1 AS REAL) BETWEEN 390 AND 459 THEN 'Circulatory'

        -- Respiratory
        WHEN CAST(diag_1 AS REAL) BETWEEN 460 AND 519 THEN 'Respiratory'

        -- Digestive
        WHEN CAST(diag_1 AS REAL) BETWEEN 520 AND 579 THEN 'Digestive'

        -- Genitourinary
        WHEN CAST(diag_1 AS REAL) BETWEEN 580 AND 629 THEN 'Genitourinary'

        -- Injury
        WHEN CAST(diag_1 AS REAL) BETWEEN 800 AND 999 THEN 'Injury'

        ELSE 'Other'

    END AS diagnosis_group,

    COUNT(*) AS total_patients,

    SUM(
        CASE
            WHEN readmitted = '<30' THEN 1
            ELSE 0
        END
    ) AS readmissions,

    ROUND(
        CAST(
            SUM(
                CASE
                    WHEN readmitted = '<30' THEN 1
                    ELSE 0
                END
            ) AS FLOAT
        ) / COUNT(*) * 100,
        2
    ) AS readmission_rate_percent,

    SUM(
        CASE
            WHEN readmitted = '<30' THEN 15200
            ELSE 0
        END
    ) AS penalty_cost_usd

FROM encounters

GROUP BY diagnosis_group

ORDER BY penalty_cost_usd DESC;