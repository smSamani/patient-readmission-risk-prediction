# ============================================================
# Diabetes Readmission - CPU Optimized Modeling Script
# Logistic Regression + XGBoost + Random Forest
# RFE + Hyperparameter Tuning + Final Comparison Table
# ============================================================

import os
import time
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import RFE
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    classification_report
)

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# ============================================================
# 0. Settings
# ============================================================

DATA_PATH = os.getenv("DIABETES_ML_DATASET", "data/processed/diabetes_final_ml_dataset_encoded.csv")
TARGET_COL = "readmitted_30d"
OUTPUT_DIR = "model_outputs_cpu"

os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42

# CPU-friendly settings
CV_FOLDS = 3
N_ITER = 12
N_FEATURES_TO_SELECT = 40
RFE_STEP = 25

TEST_SIZE = 0.20

# ============================================================
# 1. Load Dataset
# ============================================================

print("=" * 100)
print("LOADING DATASET")
print("=" * 100)

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)
print("Missing values:", df.isna().sum().sum())
print("Duplicate columns:", df.columns[df.columns.duplicated()].tolist())

assert TARGET_COL in df.columns, "Target column not found."
assert df.isna().sum().sum() == 0, "Dataset contains missing values."

X = df.drop(columns=[TARGET_COL])
y = df[TARGET_COL]

print("\nX shape:", X.shape)
print("y shape:", y.shape)

print("\nTarget distribution:")
print(y.value_counts())
print(y.value_counts(normalize=True).round(4))

# ============================================================
# 2. Train/Test Split
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)

scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

print("\nTrain/Test split:")
print("X_train:", X_train.shape)
print("X_test:", X_test.shape)
print("scale_pos_weight:", round(scale_pos_weight, 2))

cv = StratifiedKFold(
    n_splits=CV_FOLDS,
    shuffle=True,
    random_state=RANDOM_STATE
)

# ============================================================
# 3. Evaluation Function
# ============================================================

def evaluate_model(model_name, model, X_test_eval, y_test_eval, selected_features, threshold=0.5):
    y_proba = model.predict_proba(X_test_eval)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test_eval, y_pred).ravel()

    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    flagged = tp + fp

    result = {
        "Model": model_name,
        "Selected Features": len(selected_features),
        "ROC-AUC": roc_auc_score(y_test_eval, y_proba),
        "PR-AUC": average_precision_score(y_test_eval, y_proba),
        "Accuracy": accuracy_score(y_test_eval, y_pred),
        "Balanced Accuracy": balanced_accuracy_score(y_test_eval, y_pred),
        "Precision": precision_score(y_test_eval, y_pred, zero_division=0),
        "Recall": recall_score(y_test_eval, y_pred, zero_division=0),
        "Specificity": specificity,
        "F1-score": f1_score(y_test_eval, y_pred, zero_division=0),
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "Patients Flagged": flagged,
        "Flagged Rate %": flagged / len(y_test_eval) * 100
    }

    print("\nClassification Report:")
    print(classification_report(y_test_eval, y_pred))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test_eval, y_pred))

    return result, y_proba, y_pred


all_results = []
selected_features_dict = {}
best_params_list = []

# ============================================================
# 4. Logistic Regression + RFE + Tuning
# ============================================================

print("\n" + "=" * 100)
print("LOGISTIC REGRESSION + RFE + HYPERPARAMETER TUNING")
print("=" * 100)

start = time.time()

scaler = StandardScaler()

X_train_scaled = pd.DataFrame(
    scaler.fit_transform(X_train),
    columns=X_train.columns,
    index=X_train.index
)

X_test_scaled = pd.DataFrame(
    scaler.transform(X_test),
    columns=X_test.columns,
    index=X_test.index
)

lr_rfe_estimator = LogisticRegression(
    class_weight="balanced",
    solver="liblinear",
    penalty="l2",
    C=0.01,
    max_iter=3000,
    random_state=RANDOM_STATE
)

lr_rfe = RFE(
    estimator=lr_rfe_estimator,
    n_features_to_select=N_FEATURES_TO_SELECT,
    step=RFE_STEP
)

lr_rfe.fit(X_train_scaled, y_train)

lr_selected_features = X_train_scaled.columns[lr_rfe.support_].tolist()

X_train_lr = X_train_scaled[lr_selected_features]
X_test_lr = X_test_scaled[lr_selected_features]

print("Selected LR features:", len(lr_selected_features))

lr_base = LogisticRegression(
    class_weight="balanced",
    solver="liblinear",
    max_iter=5000,
    random_state=RANDOM_STATE
)

lr_param_dist = {
    "C": np.logspace(-3, 1, 10),
    "penalty": ["l1", "l2"]
}

lr_search = RandomizedSearchCV(
    estimator=lr_base,
    param_distributions=lr_param_dist,
    n_iter=N_ITER,
    scoring="roc_auc",
    cv=cv,
    verbose=1,
    random_state=RANDOM_STATE,
    n_jobs=-1
)

lr_search.fit(X_train_lr, y_train)

best_lr_model = lr_search.best_estimator_

print("\nBest LR Params:")
print(lr_search.best_params_)
print("Best LR CV ROC-AUC:", round(lr_search.best_score_, 4))

lr_result, lr_proba, lr_pred = evaluate_model(
    "Logistic Regression + RFE",
    best_lr_model,
    X_test_lr,
    y_test,
    lr_selected_features
)

all_results.append(lr_result)
selected_features_dict["logistic_regression"] = lr_selected_features
best_params_list.append({
    "Model": "Logistic Regression + RFE",
    "Best CV ROC-AUC": lr_search.best_score_,
    "Best Params": str(lr_search.best_params_)
})

joblib.dump(best_lr_model, os.path.join(OUTPUT_DIR, "best_logistic_regression_rfe.pkl"))
joblib.dump(scaler, os.path.join(OUTPUT_DIR, "logistic_regression_scaler.pkl"))

print("LR total time minutes:", round((time.time() - start) / 60, 2))

# ============================================================
# 5. XGBoost CPU + RFE + Tuning
# ============================================================

print("\n" + "=" * 100)
print("XGBOOST CPU + RFE + HYPERPARAMETER TUNING")
print("=" * 100)

start = time.time()

xgb_rfe_estimator = XGBClassifier(
    objective="binary:logistic",
    eval_metric="auc",
    n_estimators=100,
    max_depth=3,
    learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    tree_method="hist",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

xgb_rfe = RFE(
    estimator=xgb_rfe_estimator,
    n_features_to_select=N_FEATURES_TO_SELECT,
    step=RFE_STEP
)

xgb_rfe.fit(X_train, y_train)

xgb_selected_features = X_train.columns[xgb_rfe.support_].tolist()

X_train_xgb = X_train[xgb_selected_features]
X_test_xgb = X_test[xgb_selected_features]

print("Selected XGBoost features:", len(xgb_selected_features))

xgb_base = XGBClassifier(
    objective="binary:logistic",
    eval_metric="auc",
    scale_pos_weight=scale_pos_weight,
    tree_method="hist",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

xgb_param_dist = {
    "n_estimators": [100, 200, 300],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "subsample": [0.7, 0.8, 0.9],
    "colsample_bytree": [0.7, 0.8, 0.9],
    "min_child_weight": [1, 3, 5, 7],
    "gamma": [0, 0.1, 0.3],
    "reg_alpha": [0, 0.01, 0.1],
    "reg_lambda": [1, 2, 5]
}

# Important:
# XGBoost itself uses CPU parallelism, so RandomizedSearchCV stays n_jobs=1
xgb_search = RandomizedSearchCV(
    estimator=xgb_base,
    param_distributions=xgb_param_dist,
    n_iter=N_ITER,
    scoring="roc_auc",
    cv=cv,
    verbose=1,
    random_state=RANDOM_STATE,
    n_jobs=1
)

xgb_search.fit(X_train_xgb, y_train)

best_xgb_model = xgb_search.best_estimator_

print("\nBest XGBoost Params:")
print(xgb_search.best_params_)
print("Best XGBoost CV ROC-AUC:", round(xgb_search.best_score_, 4))

xgb_result, xgb_proba, xgb_pred = evaluate_model(
    "XGBoost CPU + RFE",
    best_xgb_model,
    X_test_xgb,
    y_test,
    xgb_selected_features
)

all_results.append(xgb_result)
selected_features_dict["xgboost"] = xgb_selected_features
best_params_list.append({
    "Model": "XGBoost CPU + RFE",
    "Best CV ROC-AUC": xgb_search.best_score_,
    "Best Params": str(xgb_search.best_params_)
})

joblib.dump(best_xgb_model, os.path.join(OUTPUT_DIR, "best_xgboost_rfe.pkl"))

print("XGBoost total time minutes:", round((time.time() - start) / 60, 2))

# ============================================================
# 6. Random Forest + RFE + Tuning
# ============================================================

print("\n" + "=" * 100)
print("RANDOM FOREST + RFE + HYPERPARAMETER TUNING")
print("=" * 100)

start = time.time()

# Lightweight RFE estimator to avoid wasting 1 hour
rf_rfe_estimator = RandomForestClassifier(
    n_estimators=80,
    max_depth=12,
    class_weight="balanced",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

rf_rfe = RFE(
    estimator=rf_rfe_estimator,
    n_features_to_select=N_FEATURES_TO_SELECT,
    step=RFE_STEP
)

rf_rfe.fit(X_train, y_train)

rf_selected_features = X_train.columns[rf_rfe.support_].tolist()

X_train_rf = X_train[rf_selected_features]
X_test_rf = X_test[rf_selected_features]

print("Selected RF features:", len(rf_selected_features))

rf_base = RandomForestClassifier(
    class_weight="balanced",
    random_state=RANDOM_STATE,
    n_jobs=1
)

rf_param_dist = {
    "n_estimators": [150, 250, 350],
    "max_depth": [8, 12, 16, None],
    "min_samples_split": [5, 10, 20],
    "min_samples_leaf": [2, 4, 8],
    "max_features": ["sqrt", "log2", 0.5],
    "bootstrap": [True, False]
}

# RandomizedSearchCV handles parallel jobs
rf_search = RandomizedSearchCV(
    estimator=rf_base,
    param_distributions=rf_param_dist,
    n_iter=N_ITER,
    scoring="roc_auc",
    cv=cv,
    verbose=1,
    random_state=RANDOM_STATE,
    n_jobs=-1
)

rf_search.fit(X_train_rf, y_train)

best_rf_model = rf_search.best_estimator_

print("\nBest RF Params:")
print(rf_search.best_params_)
print("Best RF CV ROC-AUC:", round(rf_search.best_score_, 4))

rf_result, rf_proba, rf_pred = evaluate_model(
    "Random Forest + RFE",
    best_rf_model,
    X_test_rf,
    y_test,
    rf_selected_features
)

all_results.append(rf_result)
selected_features_dict["random_forest"] = rf_selected_features
best_params_list.append({
    "Model": "Random Forest + RFE",
    "Best CV ROC-AUC": rf_search.best_score_,
    "Best Params": str(rf_search.best_params_)
})

joblib.dump(best_rf_model, os.path.join(OUTPUT_DIR, "best_random_forest_rfe.pkl"))

print("Random Forest total time minutes:", round((time.time() - start) / 60, 2))

# ============================================================
# 7. Final Model Comparison Table
# ============================================================

model_results = pd.DataFrame(all_results)

metric_cols = [
    "Model",
    "Selected Features",
    "ROC-AUC",
    "PR-AUC",
    "Accuracy",
    "Balanced Accuracy",
    "Precision",
    "Recall",
    "Specificity",
    "F1-score",
    "TP",
    "FP",
    "FN",
    "TN",
    "Patients Flagged",
    "Flagged Rate %"
]

model_results = model_results[metric_cols].round(4)

print("\n" + "=" * 140)
print("FINAL MODEL COMPARISON TABLE")
print("=" * 140)
print(model_results.to_string(index=False))

model_results.to_csv(
    os.path.join(OUTPUT_DIR, "final_model_comparison_logreg_xgb_rf_rfe.csv"),
    index=False
)

# ============================================================
# 8. Save Selected Features + Best Params
# ============================================================

for model_name, features in selected_features_dict.items():
    pd.DataFrame({"feature": features}).to_csv(
        os.path.join(OUTPUT_DIR, f"{model_name}_rfe_selected_features.csv"),
        index=False
    )

best_params_summary = pd.DataFrame(best_params_list)

best_params_summary.to_csv(
    os.path.join(OUTPUT_DIR, "final_best_hyperparameters_summary.csv"),
    index=False
)

# Prediction outputs
pd.DataFrame({
    "actual": y_test.values,
    "lr_probability": lr_proba,
    "xgb_probability": xgb_proba,
    "rf_probability": rf_proba,
    "lr_prediction": lr_pred,
    "xgb_prediction": xgb_pred,
    "rf_prediction": rf_pred
}).to_csv(
    os.path.join(OUTPUT_DIR, "test_set_model_predictions.csv"),
    index=False
)

print("\nSaved outputs in folder:", OUTPUT_DIR)
print("- final_model_comparison_logreg_xgb_rf_rfe.csv")
print("- final_best_hyperparameters_summary.csv")
print("- *_rfe_selected_features.csv")
print("- test_set_model_predictions.csv")
print("- best model .pkl files")
