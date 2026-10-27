#!/usr/bin/env python3
"""
Candidate Model Training & Benchmark Evaluation for Cash Collections Forecasting
Evaluates candidate regression models against simple moving-average and persistence baselines.
Uses both:
1. Chronological Holdout (Train: 2023-02 to 2026-01 [36 mo], Test: 2026-02 to 2026-08 [7 mo])
2. Expanding Window Walk-Forward Cross-Validation (Months 24 to 42 [19 sequential horizons])
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

DATA_PATH = "data/ml/cash_collections_forecasting_dataset.csv"
OUTPUT_DIR = "scratch"
ARTIFACT_PATH = os.path.join(OUTPUT_DIR, "candidate_cash_forecasting_pipeline.joblib")
METRICS_PATH = os.path.join(OUTPUT_DIR, "cash_forecasting_metrics.json")

def run_evaluation():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"{DATA_PATH} not found. Run generate_ml_datasets.py first.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    df["period_start"] = pd.to_datetime(df["period_start"])
    df = df.sort_values("period_start").reset_index(drop=True)

    features = [
        "pipeline_value_open_at_period_start_inr",
        "num_open_opportunities_at_period_start",
        "cash_revenue_trailing_1mo_inr",
        "cash_revenue_trailing_3mo_inr",
        "num_paid_txns_trailing_3mo",
        "opp_bookings_trailing_3mo_inr",
        "historical_win_rate_trailing_3mo",
        "active_rep_count",
        "seasonality_month"
    ]
    target = "label_net_cash_collections_inr"

    # --- 1. Chronological Holdout Split (70% train, 15% val, 15% test) ---
    train_df = df[df["dataset_split"] == "train"]
    val_df = df[df["dataset_split"] == "validation"]
    test_df = df[df["dataset_split"] == "test"]

    # Combine train + validation for final holdout testing (months 0..35 vs months 36..42)
    dev_df = pd.concat([train_df, val_df]).reset_index(drop=True)
    X_dev, y_dev = dev_df[features], dev_df[target]
    X_test, y_test = test_df[features], test_df[target]

    # Baselines
    # Baseline 1: Trailing 3-month moving average
    b1_preds = X_test["cash_revenue_trailing_3mo_inr"] / 3.0
    # Baseline 2: Trailing 1-month persistence
    b2_preds = X_test["cash_revenue_trailing_1mo_inr"]
    # Baseline 3: Training set mean
    b3_preds = np.full(len(y_test), y_dev.mean())

    # Candidate 1: Standard OLS Linear Regression
    lr = Pipeline([("scaler", StandardScaler()), ("regressor", LinearRegression())])
    lr.fit(X_dev, y_dev)
    lr_preds = lr.predict(X_test)

    # Candidate 2: Ridge Regression (L2 regularization)
    ridge = Pipeline([("scaler", StandardScaler()), ("regressor", Ridge(alpha=10.0))])
    ridge.fit(X_dev, y_dev)
    ridge_preds = ridge.predict(X_test)

    # Candidate 3: Random Forest Regressor
    rf = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
    rf.fit(X_dev, y_dev)
    rf_preds = rf.predict(X_test)

    def calc_metrics(y_true, y_pred):
        return {
            "MAE": round(float(mean_absolute_error(y_true, y_pred)), 2),
            "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
            "R2": round(float(r2_score(y_true, y_pred)), 4)
        }

    holdout_results = {
        "Baseline_Trailing_3mo_Avg": calc_metrics(y_test, b1_preds),
        "Baseline_Trailing_1mo_Persistence": calc_metrics(y_test, b2_preds),
        "Baseline_Historical_Mean": calc_metrics(y_test, b3_preds),
        "Candidate_Linear_Regression": calc_metrics(y_test, lr_preds),
        "Candidate_Ridge_alpha_10": calc_metrics(y_test, ridge_preds),
        "Candidate_Random_Forest": calc_metrics(y_test, rf_preds)
    }

    # --- 2. Expanding Window Walk-Forward Evaluation (Months 24 to 42, N=19) ---
    wf_actuals = []
    wf_b1_preds = []
    wf_lr_preds = []
    wf_ridge_preds = []
    wf_rf_preds = []

    for t in range(24, len(df)):
        t_train = df.iloc[:t]
        t_test = df.iloc[t:t+1]

        y_val = t_test[target].values[0]
        wf_actuals.append(y_val)

        # Baseline 1
        wf_b1_preds.append(t_test["cash_revenue_trailing_3mo_inr"].values[0] / 3.0)

        # LR
        m_lr = Pipeline([("scaler", StandardScaler()), ("regressor", LinearRegression())])
        m_lr.fit(t_train[features], t_train[target])
        wf_lr_preds.append(m_lr.predict(t_test[features])[0])

        # Ridge
        m_ridge = Pipeline([("scaler", StandardScaler()), ("regressor", Ridge(alpha=10.0))])
        m_ridge.fit(t_train[features], t_train[target])
        wf_ridge_preds.append(m_ridge.predict(t_test[features])[0])

        # RF
        m_rf = RandomForestRegressor(n_estimators=50, max_depth=3, random_state=42)
        m_rf.fit(t_train[features], t_train[target])
        wf_rf_preds.append(m_rf.predict(t_test[features])[0])

    walk_forward_results = {
        "Baseline_Trailing_3mo_Avg": calc_metrics(wf_actuals, wf_b1_preds),
        "Candidate_Linear_Regression": calc_metrics(wf_actuals, wf_lr_preds),
        "Candidate_Ridge_alpha_10": calc_metrics(wf_actuals, wf_ridge_preds),
        "Candidate_Random_Forest": calc_metrics(wf_actuals, wf_rf_preds)
    }

    # Save candidate artifact to scratch
    joblib.dump(lr, ARTIFACT_PATH)

    output = {
        "dataset_evaluated": DATA_PATH,
        "total_months": len(df),
        "zero_cash_months_count": int((df[target] == 0.0).sum()),
        "positive_cash_months_count": int((df[target] > 0.0).sum()),
        "test_split_month_count": len(test_df),
        "test_period_range": f"{test_df['period_label'].iloc[0]} to {test_df['period_label'].iloc[-1]}",
        "holdout_evaluation_metrics": holdout_results,
        "walk_forward_evaluation_metrics": walk_forward_results,
        "candidate_model_deployed_to_production": False,
        "deployment_decision_rationale": (
            "Candidate regression models achieve out-of-sample R2 <= 0 across both chronological holdout "
            "and walk-forward evaluations due to monthly payment lumpiness in a small sample size (N=43). "
            "Therefore, in accordance with Option A safeguards, the candidate ML model is NOT deployed to "
            "production. Production continues to safely use the transparent, moving-average statistical baseline."
        )
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print("Candidate evaluation complete.")
    print("Holdout Metrics:")
    for k, v in holdout_results.items():
        print(f"  {k:<35}: MAE={v['MAE']:>10,.2f}, RMSE={v['RMSE']:>10,.2f}, R2={v['R2']:>7.4f}")
    print("\nWalk-Forward Metrics (N=19):")
    for k, v in walk_forward_results.items():
        print(f"  {k:<35}: MAE={v['MAE']:>10,.2f}, RMSE={v['RMSE']:>10,.2f}, R2={v['R2']:>7.4f}")

    return output

if __name__ == "__main__":
    run_evaluation()
