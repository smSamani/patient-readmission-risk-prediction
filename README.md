# Patient Readmission Risk Prediction

A machine learning and clinical decision support project for predicting 30-day hospital readmission risk in diabetes patient encounters. The repository combines predictive modeling, SQL analysis, explainability, Tableau dashboard assets, and a full-stack web demo for exploring patient risk profiles.

## Project Summary

Hospital readmissions are costly, operationally disruptive, and often preventable when high-risk patients are identified early. This project builds an end-to-end readmission risk workflow that turns historical encounter data into actionable risk scores, model explanations, and patient-facing review tools.

The solution includes:

- Data preparation and feature engineering for diabetes patient encounters
- Baseline and tuned machine learning models for 30-day readmission prediction
- SHAP-based feature importance and model interpretation
- SQL analysis for clinical and operational readmission drivers
- Tableau dashboard assets for visual analytics
- A FastAPI and React web demo for patient queue review, chart exploration, risk summaries, interventions, and AI-assisted navigation

## Key Results

The best XGBoost model improved over the earlier baseline while maintaining clinically useful recall for the readmitted class.

| Model | ROC-AUC | PR-AUC | Recall | F1-score |
| --- | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.652 | 0.207 | 0.535 | 0.264 |
| XGBoost Default | 0.677 | 0.229 | 0.590 | 0.278 |
| XGBoost Tuned | 0.677 | 0.228 | 0.567 | 0.281 |
| Random Forest | 0.666 | 0.216 | 0.506 | 0.274 |
| LightGBM | 0.674 | 0.227 | 0.563 | 0.278 |

The final pipeline was trained on 99,340 cleaned encounters. The most important risk drivers included prior inpatient utilization, discharge disposition, total prior utilization, age, number of diagnoses, time in hospital, diagnosis group, medication count, and lab procedure volume.

## Repository Structure

```text
.
├── SQL/                         # SQL queries for clinical and operational analysis
├── WEB Demo/                    # FastAPI backend, React frontend, and demo SQLite data
├── dashboard/                   # Tableau packaged workbook and dashboard screenshots
├── figures/                     # Model evaluation and explainability visualizations
├── model_outputs_cpu/           # Lightweight model result tables
├── model_outputs_islam_stacking_cpu/
│   └── *.csv                    # Stacking experiment summaries
├── models/                      # Training scripts, excluding serialized model binaries
├── notebooks/                   # EDA, preprocessing, modeling, and rebuild notebooks
├── reports/                     # Written SQL findings
├── results/                     # Final metrics, thresholds, predictions, and SHAP summaries
└── src/                         # Reusable Python pipeline modules
```

## Machine Learning Workflow

The modeling workflow is organized around reproducible scripts and notebooks:

1. Clean and prepare encounter-level data.
2. Engineer readmission-focused clinical and utilization features.
3. Train multiple classifiers, including Logistic Regression, Random Forest, XGBoost, LightGBM, and stacking models.
4. Compare models with ROC-AUC, PR-AUC, recall, F1-score, confusion matrices, and threshold sensitivity.
5. Explain predictions using SHAP global importance and top feature summaries.

The repository intentionally excludes serialized `.pkl` model files so the project remains lightweight and suitable for GitHub. Models can be regenerated from the included scripts when the source data is available.

## SQL Analysis

The `SQL/` directory contains analysis queries covering:

- Baseline readmission penalty analysis
- Age group risk patterns
- A1C testing gaps
- Diagnosis group readmission burden
- Prior utilization and readmission risk
- Tableau-ready dataset preparation

The written SQL findings are available in `reports/SQL_Findings_Report.md`.

## Web Demo

The `WEB Demo/` folder contains a local clinical intelligence demo:

- FastAPI backend with modular routers for patients, risk, SHAP, interventions, summaries, clinical views, and AI routing
- React and Vite frontend with patient queue, chart, and clinical portal pages
- Demo SQLite database for local exploration
- Public lab report demo assets used by the frontend

### Backend

```bash
cd "WEB Demo/backend"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

By default, the backend reads:

```text
WEB Demo/diabetes_readmission_demo.sqlite
```

You can override the database path with:

```bash
export DIABETES_READMISSION_DB="/absolute/path/to/diabetes_readmission_demo.sqlite"
```

Optional Gemini-powered features require an environment variable:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

No API keys are committed to this repository.

### Frontend

```bash
cd "WEB Demo/frontend"
npm install
npm run dev
```

The frontend uses `VITE_API_BASE_URL` when provided and otherwise defaults to:

```text
http://127.0.0.1:8000
```

## Python Environment

Install the core Python dependencies from the project root:

```bash
pip install -r requirements.txt
```

Training scripts that expect the final encoded dataset can use:

```bash
export DIABETES_ML_DATASET="data/processed/diabetes_final_ml_dataset_encoded.csv"
python models/train_models_cpu.py
```

## Visual Outputs

The `figures/` directory includes:

- ROC curve
- Precision-recall curve
- Confusion matrix
- Calibration curve
- SHAP global importance
- SHAP beeswarm plot

The `dashboard/` directory includes a Tableau packaged workbook and dashboard screenshots.

## Data and Artifact Policy

This repository is prepared as a clean GitHub release. The following files are intentionally excluded:

- Raw and processed datasets
- Local SQLite databases, except the small web demo database
- Serialized `.pkl` and `.joblib` model artifacts
- Virtual environments, caches, build outputs, and OS metadata
- Secret files such as `.env`
- Local-only Tableau temporary files

This keeps the repository small, reproducible, and safe to share.

## Limitations

This project is a research and portfolio implementation, not a deployed medical device. Predictions should not be used as the sole basis for clinical decisions. Model performance depends on the source data, preprocessing assumptions, feature availability, and local validation in the target care setting.

## License

This project is released under the MIT License.
