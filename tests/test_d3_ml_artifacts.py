import pytest
import os
import joblib
import json
import pandas as pd
import numpy as np

MODELS_DIR = 'backend/ml/models'
META_FILE = os.path.join(MODELS_DIR, 'model_metadata.json')

EXPECTED_MODELS = [
    "lead_conversion_pipeline",
    "lead_scoring_pipeline",
    "sales_forecasting_pipeline",
    "customer_segmentation_pipeline",
    "churn_prediction_pipeline"
]

@pytest.fixture
def metadata():
    assert os.path.exists(META_FILE), "model_metadata.json is missing"
    with open(META_FILE, 'r') as f:
        return json.load(f)

def test_artifacts_exist(metadata):
    assert len(metadata) == len(EXPECTED_MODELS)
    
    for model_base in EXPECTED_MODELS:
        path = os.path.join(MODELS_DIR, f"{model_base}.joblib")
        assert os.path.exists(path), f"Artifact missing: {path}"

def test_artifacts_loadable():
    for model_base in EXPECTED_MODELS:
        path = os.path.join(MODELS_DIR, f"{model_base}.joblib")
        pipeline = joblib.load(path)
        assert hasattr(pipeline, "predict"), f"{model_base} pipeline missing predict method"
        assert hasattr(pipeline, "steps"), f"{model_base} is not a pipeline"

def test_metadata_structure(metadata):
    for m in metadata:
        assert "model_name" in m
        assert "dataset" in m
        assert "artifact_filename" in m
        assert "training_date" in m
        assert "feature_names" in m

def test_lead_conversion_inference(metadata):
    meta = next(m for m in metadata if "conversion" in m["artifact_filename"])
    features = meta["feature_names"]
    
    # Create dummy data matching features
    dummy_data = {f: [0] if "is_" in f else ["Test"] if "company_" in f else [10] for f in features}
    df = pd.DataFrame(dummy_data)
    
    path = os.path.join(MODELS_DIR, meta["artifact_filename"])
    pipeline = joblib.load(path)
    
    try:
        pred = pipeline.predict(df)
        prob = pipeline.predict_proba(df)
        assert len(pred) == 1
        assert len(prob) == 1
    except Exception as e:
        pytest.fail(f"Inference failed on Lead Conversion: {e}")

def test_sales_forecasting_inference(metadata):
    meta = next(m for m in metadata if "forecasting" in m["artifact_filename"])
    features = meta["feature_names"]
    
    # Create dummy data
    dummy_data = {f: [0] for f in features}
    for f in features:
        if "label" in f or "status" in f or "name" in f:
            dummy_data[f] = ["Test"]
    
    df = pd.DataFrame(dummy_data)
    
    path = os.path.join(MODELS_DIR, meta["artifact_filename"])
    pipeline = joblib.load(path)
    
    try:
        pred = pipeline.predict(df)
        assert len(pred) == 1
        assert isinstance(pred[0], (float, np.floating)), "Forecasting output must be float"
    except Exception as e:
        pytest.fail(f"Inference failed on Sales Forecasting: {e}")
