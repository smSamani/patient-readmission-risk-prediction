-- A1C Testing Gap and Readmission Impact

SELECT 
    COALESCE(A1Cresult, 'Not Tested') AS a1c_result,
    COUNT(*) AS total_patients,
    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS readmissions,
    ROUND(
        CAST(SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS FLOAT) 
        / COUNT(*) * 100, 
        2
    ) AS readmission_rate_percent,
    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) * 15200 AS penalty_cost_usd
FROM encounters
GROUP BY COALESCE(A1Cresult, 'Not Tested')
ORDER BY penalty_cost_usd DESC;