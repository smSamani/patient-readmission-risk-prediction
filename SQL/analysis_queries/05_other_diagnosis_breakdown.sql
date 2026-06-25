-- Breakdown of Raw diag_1 Codes Inside the "Other" Diagnosis Group

SELECT
    diag_1 AS raw_diagnosis_code,
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

WHERE
    NOT (
        diag_1 LIKE '250%'
        OR CAST(diag_1 AS REAL) BETWEEN 390 AND 459
        OR CAST(diag_1 AS REAL) BETWEEN 460 AND 519
        OR CAST(diag_1 AS REAL) BETWEEN 520 AND 579
        OR CAST(diag_1 AS REAL) BETWEEN 580 AND 629
        OR CAST(diag_1 AS REAL) BETWEEN 800 AND 999
    )

GROUP BY diag_1

HAVING COUNT(*) >= 100

ORDER BY penalty_cost_usd DESC

LIMIT 20;