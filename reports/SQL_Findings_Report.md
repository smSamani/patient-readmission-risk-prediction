# SQL Analytics Findings

---

## 1. Baseline 30-Day Readmission & Financial Penalty

### Business Question
What is the overall scale of the hospital readmission problem?

### Key Findings
- Total patient encounters: 101,766
- Readmissions within 30 days: 11,357
- Overall 30-day readmission rate: 11.16%
- Estimated annual CMS penalty exposure: ~$172.6M

### Business Insight
The analysis reveals a substantial operational and financial burden associated with diabetic patient readmissions. The estimated penalty exposure suggests that reducing avoidable readmissions could create significant financial savings while improving patient outcomes.

---

## 2. High-Risk Age Group Analysis

### Business Question
Which age groups contribute most significantly to readmission risk and financial burden?

### Key Findings
- Patients aged 20–30 show the highest readmission rate percentage.
- Patients aged 70–80 generate the largest total penalty burden due to their large population size and consistently high readmission rate.

### Business Insight
Although younger patients exhibit higher proportional risk, older populations represent the primary operational and financial concern for healthcare systems. This makes elderly diabetic patients a high-priority intervention group.

---

## 3. A1C Testing Gap & Clinical Assessment Risk

### Business Question
Does lack of HbA1c testing correlate with higher readmission risk?

### Key Findings
- More than 80% of patients were not tested for HbA1c.
- Untested patients showed the highest readmission rate (11.42%).
- Untested patients also generated the largest financial penalty exposure.

### Business Insight
The findings suggest that lack of clinical assessment may be associated with poorer patient outcomes. Since HbA1c testing is operationally inexpensive relative to readmission penalties, improving testing coverage could represent a cost-effective intervention opportunity.

---

---

## 4. Diagnosis Group Penalty Analysis

### Business Question
Which primary diagnosis categories among diabetic patient encounters generate the highest 30-day readmission penalty exposure?

### Why This Analysis Was Needed
The raw `diag_1` column contains ICD-based medical codes such as `428`, `414`, and `250.83`. These codes are not meaningful for non-technical stakeholders. To make the analysis suitable for a managerial dashboard, the raw diagnosis codes were grouped into broader clinical categories.

### Initial Finding
The first diagnosis grouping showed that Circulatory conditions generated the highest estimated penalty exposure, while the Other category was also very large. This indicated that the initial grouping was too broad and that important clinical patterns were still hidden inside Other.

### Refinement Step
To investigate this issue, an additional audit query was created:

`05_other_diagnosis_breakdown.sql`

This query identified the highest-cost raw diagnosis codes that were being classified as Other. The purpose was not to create a final dashboard chart, but to improve the diagnosis grouping logic used in the master Tableau dataset.

### Updated Diagnosis Grouping
The master Tableau dataset query was updated to classify diagnosis codes into more meaningful categories:

- Diabetes
- Circulatory
- Respiratory
- Digestive
- Genitourinary
- Injury
- Infectious
- Neoplasms
- Endocrine/Metabolic
- Musculoskeletal
- Symptoms
- Other

### Key Findings
- Circulatory conditions remained the largest source of estimated penalty exposure.
- Diabetes itself was not the largest financial burden.
- The Other category was reduced after refining the ICD grouping logic.
- New categories such as Symptoms, Endocrine/Metabolic, Neoplasms, Infectious, and Musculoskeletal improved clinical interpretability.
- The refined grouping made the dashboard more useful for hospital managers because it reduced ambiguity.

### Business Insight
The analysis shows that the financial burden of diabetic readmissions is not driven only by diabetes as the primary diagnosis. A large share of the burden comes from diabetic patients admitted with circulatory and other comorbidity-related conditions. This suggests that readmission reduction strategies should consider broader chronic disease and cardiovascular risk management, not only diabetes-specific care.

### Managerial Interpretation
For hospital operations managers, this supports better resource allocation. Instead of treating all diabetic readmissions as one broad problem, the hospital can identify which clinical pathways create the highest financial exposure and prioritise targeted interventions accordingly.

### Important Note
This was an iterative refinement process. The first diagnosis grouping revealed a limitation, the Other category was investigated, and the master BI dataset was improved. This demonstrates analytical maturity because the dashboard logic was not accepted blindly; it was tested, challenged, and refined.

### Limitation
The diagnosis grouping is still a simplified abstraction of ICD codes. Some cases remain in Other because real healthcare data contains heterogeneous, missing, or difficult-to-classify diagnosis codes. Future work may further improve this using more complete ICD mapping tables or multi-diagnosis profiling across `diag_1`, `diag_2`, and `diag_3`.

---

## 5. Prior Utilization Risk & Readmission Burden Analysis

### Business Question
Does previous hospital service use help identify which patient groups create the highest 30-day readmission risk and financial burden?

### Why This Analysis Was Needed
Previous hospital utilization is an important operational signal because it shows whether a patient has recently interacted with the healthcare system before the current encounter. In this dataset, prior utilization is represented by three fields:

- `number_inpatient`
- `number_emergency`
- `number_outpatient`

These variables were combined into a new utilization measure:

`prior_utilization_total = number_inpatient + number_emergency + number_outpatient`

The goal was to understand whether readmission risk is concentrated mainly among historically heavy users of hospital services, or whether a large part of the burden also comes from patients with no or limited recorded prior utilization.

### Query 6 — Readmission Risk by Prior Utilization Group

Patients were grouped into four prior utilization levels:

- `0 - No Prior Utilization`
- `1-2 - Low Prior Utilization`
- `3-5 - Medium Prior Utilization`
- `6+ - High Prior Utilization`

#### Key Findings

| Prior Utilization Group | Total Encounters | 30-Day Readmissions | Readmission Rate | Estimated Penalty Exposure |
|---|---:|---:|---:|---:|
| 6+ - High Prior Utilization | 4,425 | 1,129 | 25.51% | $17.2M |
| 3-5 - Medium Prior Utilization | 11,510 | 1,887 | 16.39% | $28.7M |
| 1-2 - Low Prior Utilization | 30,003 | 3,777 | 12.59% | $57.4M |
| 0 - No Prior Utilization | 55,828 | 4,564 | 8.18% | $69.4M |

### Business Insight
Readmission risk increases clearly as prior utilization increases. Patients with 6 or more prior inpatient, emergency, or outpatient visits had a 25.51% readmission rate, compared with 8.18% for patients with no recorded prior utilization.

This suggests that high-utilization patients are a concentrated high-risk segment. From a hospital operations perspective, these patients may require closer monitoring, stronger discharge planning, or more proactive follow-up because they are much more likely to return within 30 days.

### Query 7 — Readmission Burden Among Patients Readmitted Within 30 Days

A second query focused only on patients who were actually readmitted within 30 days. The purpose was to understand where the total readmission burden came from.

#### Key Findings

| Prior Utilization Group | 30-Day Readmission Count | Share of 30-Day Readmissions | Estimated Penalty Exposure |
|---|---:|---:|---:|
| 0 - No Prior Utilization | 4,564 | 40.19% | $69.4M |
| 1-2 - Low Prior Utilization | 3,777 | 33.26% | $57.4M |
| 3-5 - Medium Prior Utilization | 1,887 | 16.62% | $28.7M |
| 6+ - High Prior Utilization | 1,129 | 9.94% | $17.2M |

### Business Insight
Although high-utilization patients have the highest individual readmission risk, most of the total 30-day readmission burden comes from patients with no or low recorded prior utilization.

Together, the `0` and `1-2` utilization groups account for:

- 73.45% of all 30-day readmissions
- approximately $126.8M in estimated penalty exposure

This creates an important managerial insight: focusing only on historically heavy users may miss a large share of total readmission burden. Hospitals may need a more advanced risk identification approach that uses multiple signals, not just prior utilization history.

### Managerial Interpretation
This analysis supports two complementary decisions:

1. High-utilization patients should be treated as a priority risk segment because their readmission rate is substantially higher.
2. No/low-utilization patients should not be ignored, because they represent the largest share of total readmission volume and estimated financial exposure.

For hospital managers, this means readmission reduction cannot rely only on simple rules such as “prior hospital users are high-risk.” The burden is broader and requires a more sophisticated system for early risk detection.

### Connection to Future AI Solution
This finding strengthens the business case for the future Discharge Planner dashboard and ML-based risk scoring system.

A predictive model can combine multiple patient-level signals, such as:

- prior utilization history,
- age,
- diagnosis category,
- A1C testing status,
- number of medications,
- length of stay,
- and number of diagnoses.

This supports the transition from descriptive dashboarding to proactive, explainable decision support using ML and SHAP.

### Limitation
This analysis is observational and does not prove that prior utilization directly causes readmission. It shows an association between historical service use and readmission outcomes. Further modeling is needed to assess how strongly prior utilization contributes when combined with other patient risk factors.

