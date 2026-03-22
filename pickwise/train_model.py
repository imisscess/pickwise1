from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

from pickwise.utils.text_preprocessing import preprocess_for_model


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "intents_dataset.csv"
MODEL_PATH = BASE_DIR / "models" / "intent_model.pkl"


def load_dataset():
    df = pd.read_csv(DATA_PATH)
    if "question" not in df.columns or "intent" not in df.columns:
        raise ValueError("intents_dataset.csv must contain 'question' and 'intent' columns.")
    df["processed"] = df["question"].astype(str).apply(preprocess_for_model)
    return df


def train_and_save():
    df = load_dataset()
    X = df["processed"].values
    y = df["intent"].values

    pipeline = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            # Let scikit-learn choose the appropriate multi_class setting
            ("clf", LogisticRegression(max_iter=200)),
        ]
    )

    pipeline.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved intent model to {MODEL_PATH}")


if __name__ == "__main__":
    train_and_save()

