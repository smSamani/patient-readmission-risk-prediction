# ============================================================
# Islam et al. (2025) Inspired Stacking Ensemble Test
# Diabetes 30-Day Readmission Prediction
# CPU-Optimized for MacBook M1 Pro
# ============================================================

import os
import time
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
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
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    StackingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier

from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

warnings.filterwarnings("ignore")

# Try LightGBM
try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("LightGBM is not installed. LightGBM model will be skipped.")
    print("Install with: pip install lightgbm")

# ============================================================
# 0. Settings
# ============================================================

DATA_PATH = os.getenv("DIABETES_ML_DATASET", "data/processed/diabetes_final_ml_dataset_encoded.csv")
TARGET_COL = "readmitted_30d"
OUTPUT_DIR = "model_outputs_islam_stacking_cpu"

os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42

# CPU-friendly but stronger than previous quick version
CV_FOLDS = 3
N_ITER_BASE = 20
N_ITER_META = 10

# Islam-style split:
# 70% temporary train/validation, 30% final test
# then 70/30 split on temporary set:
# final train ≈ 49%, validation ≈ 21%, test ≈ 30%
TEST_SIZE = 0.30
VALIDATION_SIZE_FROM_TEMP = 0.30

# ============================================================
# 1. Load Dataset
# ============================================================

print("=" * 120)
print("LOADING FINAL ENCODED DATASET")
print("=" * 120)

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)
print("Missing values:", df.isna().sum().sum())
print("Duplicate columns:", df.columns[df.columns.duplicated()].tolist())

assert TARGET_COL in df.columns, "Target column is missing."
assert df.shape[0] > 90000, "Dataset looks too small."
assert df.isna().sum().sum() == 0, "Dataset contains missing values."

X = df.drop(columns=[TARGET_COL])
y = df[TARGET_COL]

print("\nX shape:", X.shape)
print("y shape:", y.shape)

print("\nTarget distribution:")
print(y.value_counts())
print(y.value_counts(normalize=True).round(4))

# ============================================================
# 2. Islam-style Train / Validation / Test Split
# ============================================================

print("\n" + "=" * 120)
print("ISLAM-STYLE TRAIN / VALIDATION / TEST SPLIT")
print("=" * 120)

X_temp, X_test, y_temp, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)

X_train, X_val, y_train, y_val = train_test_split(
    X_temp,
    y_temp,
    test_size=VALIDATION_SIZE_FROM_TEMP,
    random_state=RANDOM_STATE,
    stratify=y_temp
)

print("X_train:", X_train.shape)
print("X_val:", X_val.shape)
print("X_test:", X_test.shape)

print("\ny_train distribution:")
print(y_train.value_counts(normalize=True).round(4))

print("\ny_val distribution:")
print(y_val.value_counts(normalize=True).round(4))

print("\ny_test distribution:")
print(y_test.value_counts(normalize=True).round(4))

# ============================================================
# 3. SMOTE on Training Set Only
# ============================================================

print("\n" + "=" * 120)
print("APPLYING SMOTE TO TRAINING SET ONLY")
print("=" * 120)

smote = SMOTE(random_state=RANDOM_STATE, n_jobs=-1)

X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

print("Original training shape:", X_train.shape)
print("SMOTE training shape:", X_train_smote.shape)

print("\nSMOTE class distribution:")
print(y_train_smote.value_counts(normalize=True).round(4))

# ============================================================
# 4. Evaluation Function
# ============================================================

def evaluate_model(model_name, model, X_eval, y_eval, dataset_name, threshold=0.5):
    y_proba = model.predict_proba(X_eval)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_eval, y_pred).ravel()

    return {
        "Model": model_name,
        "Dataset": dataset_name,
        "ROC-AUC": roc_auc_score(y_eval, y_proba),
        "PR-AUC": average_precision_score(y_eval, y_proba),
        "Accuracy": accuracy_score(y_eval, y_pred),
        "Balanced Accuracy": balanced_accuracy_score(y_eval, y_pred),
        "Precision": precision_score(y_eval, y_pred, zero_division=0),
        "Recall": recall_score(y_eval, y_pred, zero_division=0),
        "F1-score": f1_score(y_eval, y_pred, zero_division=0),
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn
    }


def evaluate_on_all_sets(model_name, model):
    rows = []
    rows.append(evaluate_model(model_name, model, X_train, y_train, "Train"))
    rows.append(evaluate_model(model_name, model, X_val, y_val, "Validation"))
    rows.append(evaluate_model(model_name, model, X_test, y_test, "Test"))
    return rows


def tune_model(model_name, estimator, param_dist, X_fit, y_fit, n_iter=N_ITER_BASE):
    print("\n" + "-" * 100)
    print(f"TUNING: {model_name}")
    print("-" * 100)

    cv = StratifiedKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE
    )

    search = RandomizedSearchCV(
        estimator=estimator,
        param_distributions=param_dist,
        n_iter=n_iter,
        scoring="f1",
        cv=cv,
        verbose=1,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    start = time.time()
    search.fit(X_fit, y_fit)
    elapsed = round((time.time() - start) / 60, 2)

    print(f"{model_name} tuning time minutes:", elapsed)
    print("Best params:")
    print(search.best_params_)
    print("Best CV F1:", round(search.best_score_, 4))

    return search.best_estimator_, search.best_params_, search.best_score_

# ============================================================
# 5. Base Models Before Tuning
# ============================================================

print("\n" + "=" * 120)
print("TRAINING BASE MODELS BEFORE TUNING")
print("=" * 120)

base_models_before = {}

base_models_before["Decision Tree"] = DecisionTreeClassifier(
    random_state=RANDOM_STATE
)

base_models_before["Random Forest"] = RandomForestClassifier(
    n_estimators=200,
    random_state=RANDOM_STATE,
    n_jobs=-1
)

base_models_before["Gradient Boosting"] = GradientBoostingClassifier(
    random_state=RANDOM_STATE
)

base_models_before["XGBoost"] = XGBClassifier(
    objective="binary:logistic",
    eval_metric="logloss",
    tree_method="hist",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

if LIGHTGBM_AVAILABLE:
    base_models_before["LightGBM"] = LGBMClassifier(
        objective="binary",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1
    )

base_models_before["Logistic Regression"] = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(
        max_iter=3000,
        random_state=RANDOM_STATE
    ))
])

base_models_before["MLP"] = Pipeline([
    ("scaler", StandardScaler()),
    ("model", MLPClassifier(
        hidden_layer_sizes=(64,),
        max_iter=200,
        random_state=RANDOM_STATE,
        early_stopping=True
    ))
])

base_results_before = []

for name, model in base_models_before.items():
    print(f"Training before-tuning model: {name}")
    model.fit(X_train_smote, y_train_smote)
    base_results_before.extend(evaluate_on_all_sets(f"{name} Before Tuning", model))

# ============================================================
# 6. Base Models Hyperparameter Tuning
# ============================================================

print("\n" + "=" * 120)
print("TUNING BASE MODELS WITH SMOTE TRAINING DATA")
print("=" * 120)

tuned_models = {}
best_params_records = []

# Decision Tree
dt_params = {
    "max_depth": [4, 6, 8, 10, 12, None],
    "min_samples_split": [2, 5, 10, 20],
    "min_samples_leaf": [1, 2, 4, 8],
    "criterion": ["gini", "entropy"]
}

dt_best, dt_params_best, dt_cv = tune_model(
    "Decision Tree",
    DecisionTreeClassifier(random_state=RANDOM_STATE),
    dt_params,
    X_train_smote,
    y_train_smote
)
tuned_models["Decision Tree"] = dt_best
best_params_records.append({
    "Model": "Decision Tree",
    "Best CV F1": dt_cv,
    "Best Params": str(dt_params_best)
})

# Random Forest
rf_params = {
    "n_estimators": [150, 250, 350],
    "max_depth": [8, 12, 16, None],
    "min_samples_split": [5, 10, 20],
    "min_samples_leaf": [2, 4, 8],
    "max_features": ["sqrt", "log2", 0.5],
    "bootstrap": [True, False]
}

rf_best, rf_params_best, rf_cv = tune_model(
    "Random Forest",
    RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1),
    rf_params,
    X_train_smote,
    y_train_smote
)
tuned_models["Random Forest"] = rf_best
best_params_records.append({
    "Model": "Random Forest",
    "Best CV F1": rf_cv,
    "Best Params": str(rf_params_best)
})

# Gradient Boosting
gb_params = {
    "n_estimators": [100, 200, 300],
    "learning_rate": [0.03, 0.05, 0.1],
    "max_depth": [2, 3, 4],
    "subsample": [0.7, 0.8, 1.0],
    "min_samples_leaf": [1, 3, 5]
}

gb_best, gb_params_best, gb_cv = tune_model(
    "Gradient Boosting",
    GradientBoostingClassifier(random_state=RANDOM_STATE),
    gb_params,
    X_train_smote,
    y_train_smote
)
tuned_models["Gradient Boosting"] = gb_best
best_params_records.append({
    "Model": "Gradient Boosting",
    "Best CV F1": gb_cv,
    "Best Params": str(gb_params_best)
})

# XGBoost
xgb_params = {
    "n_estimators": [100, 200, 300],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "subsample": [0.7, 0.8, 0.9],
    "colsample_bytree": [0.7, 0.8, 0.9],
    "min_child_weight": [1, 3, 5],
    "gamma": [0, 0.1, 0.3],
    "reg_lambda": [1, 2, 5]
}

xgb_best, xgb_params_best, xgb_cv = tune_model(
    "XGBoost",
    XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        random_state=RANDOM_STATE,
        n_jobs=1
    ),
    xgb_params,
    X_train_smote,
    y_train_smote
)
tuned_models["XGBoost"] = xgb_best
best_params_records.append({
    "Model": "XGBoost",
    "Best CV F1": xgb_cv,
    "Best Params": str(xgb_params_best)
})

# LightGBM
if LIGHTGBM_AVAILABLE:
    lgbm_params = {
        "n_estimators": [100, 200, 300],
        "learning_rate": [0.03, 0.05, 0.1],
        "max_depth": [-1, 5, 7, 10],
        "num_leaves": [31, 63, 127],
        "subsample": [0.7, 0.8, 1.0],
        "colsample_bytree": [0.7, 0.8, 1.0]
    }

    lgbm_best, lgbm_params_best, lgbm_cv = tune_model(
        "LightGBM",
        LGBMClassifier(
            objective="binary",
            random_state=RANDOM_STATE,
            n_jobs=1,
            verbose=-1
        ),
        lgbm_params,
        X_train_smote,
        y_train_smote
    )
    tuned_models["LightGBM"] = lgbm_best
    best_params_records.append({
        "Model": "LightGBM",
        "Best CV F1": lgbm_cv,
        "Best Params": str(lgbm_params_best)
    })

# Logistic Regression
lr_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(
        max_iter=5000,
        random_state=RANDOM_STATE
    ))
])

lr_params = {
    "model__C": np.logspace(-3, 2, 10),
    "model__penalty": ["l1", "l2"],
    "model__solver": ["liblinear"]
}

lr_best, lr_params_best, lr_cv = tune_model(
    "Logistic Regression",
    lr_pipeline,
    lr_params,
    X_train_smote,
    y_train_smote
)
tuned_models["Logistic Regression"] = lr_best
best_params_records.append({
    "Model": "Logistic Regression",
    "Best CV F1": lr_cv,
    "Best Params": str(lr_params_best)
})

# MLP
mlp_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", MLPClassifier(
        max_iter=250,
        random_state=RANDOM_STATE,
        early_stopping=True
    ))
])

mlp_params = {
    "model__hidden_layer_sizes": [(64,), (128,), (64, 32)],
    "model__alpha": [0.0001, 0.001, 0.01],
    "model__learning_rate_init": [0.001, 0.003, 0.01]
}

mlp_best, mlp_params_best, mlp_cv = tune_model(
    "MLP",
    mlp_pipeline,
    mlp_params,
    X_train_smote,
    y_train_smote,
    n_iter=9
)
tuned_models["MLP"] = mlp_best
best_params_records.append({
    "Model": "MLP",
    "Best CV F1": mlp_cv,
    "Best Params": str(mlp_params_best)
})

# ============================================================
# 7. Evaluate Tuned Base Models
# ============================================================

print("\n" + "=" * 120)
print("EVALUATING TUNED BASE MODELS")
print("=" * 120)

base_results_after = []

for name, model in tuned_models.items():
    print(f"Evaluating tuned model: {name}")
    base_results_after.extend(evaluate_on_all_sets(f"{name} After Tuning", model))

# ============================================================
# 8. Stacking Before Tuning
# ============================================================

print("\n" + "=" * 120)
print("STACKING ENSEMBLE BEFORE TUNING")
print("=" * 120)

# Use simpler before-tuning models
stack_estimators_before = []

for name, model in base_models_before.items():
    stack_estimators_before.append((name.replace(" ", "_").lower(), model))

stack_before = StackingClassifier(
    estimators=stack_estimators_before,
    final_estimator=GradientBoostingClassifier(random_state=RANDOM_STATE),
    stack_method="predict_proba",
    cv=5,
    n_jobs=-1,
    passthrough=False
)

start = time.time()
stack_before.fit(X_train_smote, y_train_smote)
print("Stacking before tuning time minutes:", round((time.time() - start) / 60, 2))

stack_results_before = evaluate_on_all_sets("Stacking Ensemble Before Tuning", stack_before)

# ============================================================
# 9. Stacking After Tuning with Gradient Boosting Meta-Learner
# ============================================================

print("\n" + "=" * 120)
print("STACKING ENSEMBLE AFTER TUNING - GRADIENT BOOSTING META-LEARNER")
print("=" * 120)

stack_estimators_after = []

for name, model in tuned_models.items():
    stack_estimators_after.append((name.replace(" ", "_").lower(), model))

stack_after_gb = StackingClassifier(
    estimators=stack_estimators_after,
    final_estimator=GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        random_state=RANDOM_STATE
    ),
    stack_method="predict_proba",
    cv=5,
    n_jobs=-1,
    passthrough=False
)

start = time.time()
stack_after_gb.fit(X_train_smote, y_train_smote)
print("Stacking after tuning time minutes:", round((time.time() - start) / 60, 2))

stack_results_after_gb = evaluate_on_all_sets(
    "Stacking Ensemble After Tuning - GB Meta",
    stack_after_gb
)

# ============================================================
# 10. Optional Meta-Learner Comparison
# ============================================================

print("\n" + "=" * 120)
print("META-LEARNER COMPARISON")
print("=" * 120)

meta_candidates = {
    "GB Meta": GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        random_state=RANDOM_STATE
    ),
    "LogReg Meta": LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        random_state=RANDOM_STATE
    ),
    "DecisionTree Meta": DecisionTreeClassifier(
        max_depth=4,
        random_state=RANDOM_STATE
    )
}

meta_results = []

for meta_name, meta_model in meta_candidates.items():
    print(f"Training stacking with {meta_name}")

    stack_model = StackingClassifier(
        estimators=stack_estimators_after,
        final_estimator=meta_model,
        stack_method="predict_proba",
        cv=5,
        n_jobs=-1,
        passthrough=False
    )

    stack_model.fit(X_train_smote, y_train_smote)

    rows = evaluate_on_all_sets(f"Stacking After Tuning - {meta_name}", stack_model)
    meta_results.extend(rows)

    joblib.dump(
        stack_model,
        os.path.join(OUTPUT_DIR, f"stacking_after_tuning_{meta_name.replace(' ', '_').lower()}.pkl")
    )

# ============================================================
# 11. Final Tables
# ============================================================

print("\n" + "=" * 120)
print("SAVING FINAL RESULTS")
print("=" * 120)

all_results = (
    base_results_before
    + base_results_after
    + stack_results_before
    + stack_results_after_gb
    + meta_results
)

results_df = pd.DataFrame(all_results)

metric_cols = [
    "Model",
    "Dataset",
    "ROC-AUC",
    "PR-AUC",
    "Accuracy",
    "Balanced Accuracy",
    "Precision",
    "Recall",
    "F1-score",
    "TP",
    "FP",
    "FN",
    "TN"
]

results_df = results_df[metric_cols].round(4)

# Full results
results_path = os.path.join(OUTPUT_DIR, "islam_stacking_full_results.csv")
results_df.to_csv(results_path, index=False)

# Test-only comparison
test_results = results_df[results_df["Dataset"] == "Test"].copy()
test_results = test_results.sort_values(by=["F1-score", "ROC-AUC"], ascending=False)

test_results_path = os.path.join(OUTPUT_DIR, "islam_stacking_test_results_ranked.csv")
test_results.to_csv(test_results_path, index=False)

# Best params
best_params_df = pd.DataFrame(best_params_records)
best_params_path = os.path.join(OUTPUT_DIR, "islam_base_model_best_params.csv")
best_params_df.to_csv(best_params_path, index=False)

print("\n" + "=" * 160)
print("ISLAM-STYLE TEST RESULTS RANKED BY TEST F1")
print("=" * 160)
print(test_results.to_string(index=False))

print("\nSaved outputs:")
print(results_path)
print(test_results_path)
print(best_params_path)

# Save models
for name, model in tuned_models.items():
    safe_name = name.replace(" ", "_").lower()
    joblib.dump(model, os.path.join(OUTPUT_DIR, f"tuned_{safe_name}.pkl"))

joblib.dump(stack_before, os.path.join(OUTPUT_DIR, "stacking_before_tuning.pkl"))
joblib.dump(stack_after_gb, os.path.join(OUTPUT_DIR, "stacking_after_tuning_gb_meta.pkl"))

print("\nModels saved in:", OUTPUT_DIR)
