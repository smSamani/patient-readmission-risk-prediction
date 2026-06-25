-- Baseline 30-Day Readmission KPI and Estimated Financial Penalty

SELECT 
    COUNT(*) AS total_patients,
    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS readmitted_under_30_days,
    ROUND(
        CAST(SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS FLOAT) 
        / COUNT(*) * 100, 
        2
    ) AS readmission_rate_percentage,
    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) * 15200 AS total_penalty_cost_usd
FROM encounters;