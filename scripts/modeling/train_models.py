import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, roc_auc_score, confusion_matrix, 
                             mean_absolute_error, mean_squared_error, r2_score,
                             silhouette_score, average_precision_score)
import joblib
import json
import os
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

MODELS_DIR = 'backend/ml/models'
DATA_DIR = 'data/ml'

metadata = []

def save_artifact(pipeline, name, meta_info):
    path = os.path.join(MODELS_DIR, f"{name}.joblib")
    joblib.dump(pipeline, path)
    meta_info["artifact_filename"] = f"{name}.joblib"
    meta_info["training_date"] = datetime.utcnow().isoformat()
    metadata.append(meta_info)

def build_preprocessor(categorical_features, numerical_features):
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ], remainder='drop')
    
    return preprocessor

def train_lead_conversion():
    print("Training Lead Conversion Model...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'lead_conversion_dataset.csv'))
    
    target = 'label_converted'
    drop_cols = ['ml_record_id', 'lead_id', 'company_id', 'observation_cutoff_at', 'dataset_split', target, 'lead_status']
    
    features = [c for c in df.columns if c not in drop_cols]
    
    categorical = df[features].select_dtypes(include=['object', 'bool']).columns.tolist()
    numerical = df[features].select_dtypes(include=['number']).columns.tolist()
    
    # Cast booleans to string for simple processing
    for col in categorical:
        if df[col].dtype == 'bool':
            df[col] = df[col].astype(str)
            
    X = df[features]
    y = df[target].astype(int)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    preprocessor = build_preprocessor(categorical, numerical)
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])
    pipeline.fit(X_train, y_train)
    
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.4).astype(int) # using threshold from previous logic
    
    roc = roc_auc_score(y_test, y_prob)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    meta = {
        "model_name": "Lead Conversion Prediction",
        "dataset": "lead_conversion_dataset.csv",
        "target": target,
        "feature_names": features,
        "model_type": "RandomForestClassifier",
        "random_seed": 42,
        "dataset_row_count": len(df),
        "class_distribution": {"0": int((y==0).sum()), "1": int((y==1).sum())},
        "evaluation_metrics": {
            "ROC-AUC": roc,
            "Precision": prec,
            "Recall": rec,
            "F1": f1,
            "ConfusionMatrix": cm
        }
    }
    save_artifact(pipeline, "lead_conversion_pipeline", meta)

def train_lead_scoring():
    print("Training Lead Scoring Model...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'lead_scoring_dataset.csv'))
    
    target = 'label_converted'
    drop_cols = ['ml_record_id', 'lead_id', 'company_id', 'observation_cutoff_at', 'dataset_split', target, 'lead_status']
    
    features = [c for c in df.columns if c not in drop_cols]
    categorical = df[features].select_dtypes(include=['object', 'bool']).columns.tolist()
    numerical = df[features].select_dtypes(include=['number']).columns.tolist()
    
    for col in categorical:
        if df[col].dtype == 'bool':
            df[col] = df[col].astype(str)
            
    X = df[features]
    y = df[target].astype(int)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    preprocessor = build_preprocessor(categorical, numerical)
    model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])
    pipeline.fit(X_train, y_train)
    
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    y_pred = pipeline.predict(X_test)
    
    roc = roc_auc_score(y_test, y_prob)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    meta = {
        "model_name": "Lead Scoring",
        "dataset": "lead_scoring_dataset.csv",
        "target": target,
        "feature_names": features,
        "model_type": "LogisticRegression",
        "random_seed": 42,
        "dataset_row_count": len(df),
        "class_distribution": {"0": int((y==0).sum()), "1": int((y==1).sum())},
        "evaluation_metrics": {
            "ROC-AUC": roc,
            "Precision": prec,
            "Recall": rec,
            "F1": f1,
            "ConfusionMatrix": cm
        }
    }
    save_artifact(pipeline, "lead_scoring_pipeline", meta)

def train_sales_forecasting():
    print("Training Sales Forecasting Model...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'sales_forecasting_dataset.csv'))
    
    df['period_start'] = pd.to_datetime(df['period_start'])
    df = df.sort_values('period_start')
    
    df['year'] = df['period_start'].dt.year
    
    target = 'label_actual_amount_inr'
    drop_cols = ['ml_record_id', 'department_id', 'department_name', 'period_label', 'period_start', 'dataset_split', target]
    
    features = [c for c in df.columns if c not in drop_cols]
    categorical = df[features].select_dtypes(include=['object', 'bool']).columns.tolist()
    numerical = df[features].select_dtypes(include=['number']).columns.tolist()
    
    X = df[features]
    y = df[target].fillna(0)
    
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    preprocessor = build_preprocessor(categorical, numerical)
    model = LinearRegression()
    
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('regressor', model)])
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    # Baseline
    if 'revenue_trailing_3mo_inr' in X_test.columns:
        baseline_preds = X_test['revenue_trailing_3mo_inr'] / 3.0
    else:
        baseline_preds = [y_train.mean()] * len(y_test)
    baseline_mae = mean_absolute_error(y_test, baseline_preds)
    
    meta = {
        "model_name": "Sales Forecasting",
        "dataset": "sales_forecasting_dataset.csv",
        "target": target,
        "feature_names": features,
        "model_type": "LinearRegression",
        "random_seed": None, # chron splitting
        "dataset_row_count": len(df),
        "evaluation_metrics": {
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
            "Baseline_MAE": baseline_mae
        }
    }
    save_artifact(pipeline, "sales_forecasting_pipeline", meta)

def train_customer_segmentation():
    print("Training Customer Segmentation Model...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'customer_segmentation_dataset.csv'))
    
    drop_cols = ['ml_record_id', 'customer_id', 'company_id', 'snapshot_date']
    features = [c for c in df.columns if c not in drop_cols]
    
    categorical = df[features].select_dtypes(include=['object', 'bool']).columns.tolist()
    numerical = df[features].select_dtypes(include=['number']).columns.tolist()
    
    X = df[features]
    
    preprocessor = build_preprocessor(categorical, numerical)
    model = KMeans(n_clusters=3, random_state=42)
    
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('clusterer', model)])
    pipeline.fit(X)
    
    X_processed = preprocessor.transform(X)
    clusters = pipeline.predict(X)
    sil_score = silhouette_score(X_processed, clusters)
    
    # Calculate simple cluster sizes
    unique, counts = np.unique(clusters, return_counts=True)
    cluster_sizes = dict(zip([str(u) for u in unique], [int(c) for c in counts]))
    
    # Calculate centroids on raw numerical data to keep them interpretable, but they are inside the pipeline
    # We can just extract them from the model later, for now we save the pipeline.
    
    meta = {
        "model_name": "Customer Segmentation",
        "dataset": "customer_segmentation_dataset.csv",
        "target": "None (Unsupervised)",
        "feature_names": features,
        "model_type": "KMeans",
        "random_seed": 42,
        "dataset_row_count": len(df),
        "evaluation_metrics": {
            "SilhouetteScore": float(sil_score),
            "ClusterSizes": cluster_sizes
        }
    }
    save_artifact(pipeline, "customer_segmentation_pipeline", meta)

def train_churn_prediction():
    print("Training Customer Churn Model...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'churn_prediction_dataset.csv'))
    
    target = 'label_churned_within_horizon'
    drop_cols = ['ml_record_id', 'customer_id', 'company_id', 'observation_snapshot_date', 'renewal_due_date', 'dataset_split', target]
    features = [c for c in df.columns if c not in drop_cols]
    
    categorical = df[features].select_dtypes(include=['object', 'bool']).columns.tolist()
    numerical = df[features].select_dtypes(include=['number']).columns.tolist()
    
    for col in categorical:
        if df[col].dtype == 'bool':
            df[col] = df[col].astype(str)
            
    X = df[features]
    y = df[target].astype(int)
    
    preprocessor = build_preprocessor(categorical, numerical)
    model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    roc_aucs, pr_aucs = [], []
    for tr_idx, val_idx in cv.split(X, y):
        from sklearn.base import clone
        cv_pipe = clone(pipeline)
        cv_pipe.fit(X.iloc[tr_idx], y.iloc[tr_idx])
        y_prob_cv = cv_pipe.predict_proba(X.iloc[val_idx])[:, 1]
        roc_aucs.append(roc_auc_score(y.iloc[val_idx], y_prob_cv))
        pr_aucs.append(average_precision_score(y.iloc[val_idx], y_prob_cv))
    
    pipeline.fit(X, y)
    
    meta = {
        "model_name": "Customer Churn Prediction",
        "dataset": "churn_prediction_dataset.csv",
        "target": target,
        "feature_names": features,
        "model_type": "LogisticRegression",
        "random_seed": 42,
        "dataset_row_count": len(df),
        "class_distribution": {"0": int((y==0).sum()), "1": int((y==1).sum())},
        "evaluation_metrics": {
            "CV_ROC-AUC_mean": float(np.mean(roc_aucs)),
            "CV_PR-AUC_mean": float(np.mean(pr_aucs))
        },
        "warnings": "Extremely small dataset (59 rows). CV metrics are directional. Do not oversell."
    }
    save_artifact(pipeline, "churn_prediction_pipeline", meta)

def main():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        
    train_lead_conversion()
    train_lead_scoring()
    train_sales_forecasting()
    train_customer_segmentation()
    train_churn_prediction()
    
    with open(os.path.join(MODELS_DIR, 'model_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    print("All models trained and artifacts generated.")

if __name__ == '__main__':
    main()
