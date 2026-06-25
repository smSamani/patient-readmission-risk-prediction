-- 30-Day Readmission Risk by Age Group

SELECT 
    age,
    COUNT(*) AS total_patients,
    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS readmissions,
    ROUND(
        CAST(SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS FLOAT) 
        / COUNT(*) * 100, 
        2
    ) AS readmission_rate_percent,
    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) * 15200 AS penalty_cost_usd
FROM encounters
GROUP BY age
ORDER BY penalty_cost_usd DESC;