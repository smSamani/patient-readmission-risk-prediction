SELECT
    CASE
        WHEN (number_inpatient + number_emergency + number_outpatient) = 0
            THEN '0 - No Prior Utilization'
        WHEN (number_inpatient + number_emergency + number_outpatient) BETWEEN 1 AND 2
            THEN '1-2 - Low Prior Utilization'
        WHEN (number_inpatient + number_emergency + number_outpatient) BETWEEN 3 AND 5
            THEN '3-5 - Medium Prior Utilization'
        ELSE '6+ - High Prior Utilization'
    END AS prior_utilization_group,

    COUNT(*) AS total_encounters,

    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS readmitted_30d,

    ROUND(
        100.0 * SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS readmission_rate_pct,

    SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) * 15200
        AS estimated_penalty_exposure_usd

FROM encounters
GROUP BY prior_utilization_group
ORDER BY readmission_rate_pct DESC;