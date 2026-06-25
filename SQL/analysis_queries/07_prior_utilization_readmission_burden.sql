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

    COUNT(*) AS readmitted_30d_count,

    ROUND(
        100.0 * COUNT(*) /
        (SELECT COUNT(*) FROM encounters WHERE readmitted = '<30'),
        2
    ) AS share_of_30d_readmissions_pct,

    COUNT(*) * 15200 AS estimated_penalty_exposure_usd

FROM encounters
WHERE readmitted = '<30'
GROUP BY prior_utilization_group
ORDER BY estimated_penalty_exposure_usd DESC;