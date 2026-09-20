# -*- coding: utf-8 -*-
import pandas as pd
from sklearn.pipeline import Pipeline
from pickle import load


def make_inference(in_model: Pipeline, in_data: dict) -> dict:
    """Return the result of classification for in_data using in_model."""
    df = pd.DataFrame(in_data, index=[0])
    prediction = in_model.predict(df)[0]
    probabilities = in_model.predict_proba(df)[0]

    return {
        "loan_status": "Approved" if prediction == 1 else "Rejected",
        "probability_approved": round(float(probabilities[1]), 4),
        "probability_rejected": round(float(probabilities[0]), 4),
    }


def load_model(path: str) -> Pipeline:
    """Return the model being read which stored on the path."""
    with open(path, "rb") as file:
        model: Pipeline = load(file)

    return model