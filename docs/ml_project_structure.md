# Recommended ML Project Structure

A suggested repository layout for a project that trains and serves models on the 5 ML-ready datasets in this package.

```
crm-ml/
├── data/
│   ├── raw/                    # this package's data/ml/*.csv, vendored read-only
│   └── processed/              # any additional derived features you build,
│                                #   versioned separately from raw/ (never edit raw/ in place)
├── notebooks/
│   ├── 01_eda_lead_conversion.ipynb
│   ├── 02_eda_churn.ipynb
│   └── ...                     # one per dataset; keep exploratory work out of src/
├── src/
│   ├── data/
│   │   ├── load.py             # read CSVs, apply dataset_split, basic schema checks
│   │   └── validate.py         # thin wrapper calling the package's validate_dataset.py
│   ├── features/
│   │   ├── lead_conversion.py  # any *additional* feature engineering beyond what's
│   │   ├── churn.py            #   already in the ML CSVs — must follow
│   │   └── ...                 #   ml_leakage_prevention.md's rules
│   ├── models/
│   │   ├── lead_conversion_model.py
│   │   ├── lead_scoring_model.py
│   │   ├── sales_forecast_model.py
│   │   ├── segmentation_model.py
│   │   └── churn_model.py
│   ├── evaluation/
│   │   ├── metrics.py          # classification: AUC, PR-AUC, calibration; regression:
│   │   │                        #   MAE/RMSE/MAPE for forecasting; clustering: silhouette
│   │   └── reports.py          # generates a per-model evaluation report artifact
│   └── serving/
│       ├── api.py              # the /ml/* endpoints from recommended_api_endpoints.md
│       └── schema.py           # request/response contracts, pinned per model version
├── models/                     # trained model artifacts, versioned (e.g. via DVC/MLflow),
│                                #   never committed raw to git
├── configs/
│   ├── lead_conversion.yaml    # hyperparameters, feature list, split dates
│   └── ...
├── tests/
│   ├── test_no_leakage.py      # asserts every feature column used in training has a
│   │                            #   documented-safe cutoff relationship (see below)
│   ├── test_split_chronology.py
│   └── test_model_io.py
├── Makefile / dvc.yaml          # reproducible pipeline: load -> validate -> train -> evaluate
└── requirements.txt
```

## Per-dataset modeling plan (short form — full detail in `ml_dataset_documentation.md`)

| Dataset | Task type | Suggested baseline | Suggested stronger model | Primary metric |
|---|---|---|---|---|
| lead_conversion_dataset | Binary classification | Logistic regression | Gradient-boosted trees (XGBoost/LightGBM) | PR-AUC (imbalanced, 18.3% positive) |
| lead_scoring_dataset | Binary classification, day-0 only | Logistic regression | Gradient-boosted trees | PR-AUC; calibration matters more here since scores are shown to reps |
| sales_forecasting_dataset | Regression (small N: 172 rows) | Naive seasonal baseline (last-period value) | Gradient-boosted trees or a simple time-series model (be wary of overfitting given the row count) | MAPE / MAE, evaluated only on the chronological test tail |
| customer_segmentation_dataset | Unsupervised clustering | K-means on standardized RFM features | Gaussian mixture or hierarchical clustering; compare cluster stability across snapshots | Silhouette score; business interpretability of resulting segments |
| churn_prediction_dataset | Binary classification (small N: 59 rows) | Logistic regression with strong regularization | Gradient-boosted trees only if row count grows at scale — 59 rows is too small for a complex model to generalize; flag this explicitly in any report | PR-AUC; be explicit about the small-sample caveat in any deployed-model documentation |

## Non-negotiable pipeline steps

1. **Load → validate → split → train**, in that order, every time. Never train on data that hasn't just passed `scripts/validation/validate_dataset.py` (or your project's `src/data/validate.py` wrapper around it).
2. **Respect `dataset_split` as given.** Do not re-split randomly for convenience — it was assigned chronologically specifically so evaluation reflects real deployment (train on the past, evaluate on the future). If you need a validation set for early stopping, carve it out of `train` chronologically (earliest 85% of `train` → sub-train, latest 15% → early-stopping set), never randomly.
3. **Re-run the leakage checks in `ml_leakage_prevention.md` whenever you add a feature**, not just once at project start.
4. **Log feature provenance.** Every feature that goes into a model should be traceable to a specific source-table column and cutoff rule — this is what makes a "why did the model flag this lead" explanation possible later, and what makes a future audit (like the one that produced `data_quality_report.md`) tractable.
5. **Version models and their training-data snapshot together.** Since this dataset is a fixed pilot batch today but is expected to scale later, pin which dataset version (by row-count/checksum) a given model artifact was trained on.

## Scale caveat

`sales_forecasting_dataset` (172 rows) and `churn_prediction_dataset` (59 rows) are small enough that any "stronger model" should be treated with real skepticism — a gradient-boosted model can easily memorize noise at this scale. Report cross-validated metrics with confidence intervals, not a single train/test number, and prefer the simpler baseline unless the stronger model's improvement clearly survives resampling.
