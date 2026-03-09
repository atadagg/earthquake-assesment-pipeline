"""
Top-Level Classifier — 3 independent binary classifiers

For each entry, independently predicts:
    H  — Hasar   (damage)
    Y  — Yardım  (need/help)
    B  — Bilgi   (information)

An entry can be any combination: H=1 Y=1 B=0, H=0 Y=0 B=0 (N), etc.
N (none) is implicit — all three are 0.

Training:  python classifiers/top_level_classifier.py train classifiers/data.xlsx
Inference: TopLevelClassifier().predict("enkaz altında sesler var")
           → {"H": 1, "Y": 0, "B": 0}
"""

import sys
import joblib
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

DATA_DIR = Path(__file__).parent.parent / "data"

LABELS = ["H", "Y", "B"]
MODEL_FILES = {label: str(DATA_DIR / f"model_{label}.joblib") for label in LABELS}


def _make_binary(series: pd.Series, label: str) -> pd.Series:
    """1 if label appears anywhere in the AOD string, 0 otherwise."""
    return series.apply(lambda v: 1 if label in str(v) else 0)


def _train_one(X_train, y_train, X_val, y_val, label: str):
    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=50_000, lowercase=True)
    clf   = LinearSVC(class_weight="balanced", random_state=42)

    clf.fit(tfidf.fit_transform(X_train), y_train)
    y_pred = clf.predict(tfidf.transform(X_val))

    print(f"\n=== {label} vs N{label} ===")
    print(classification_report(y_val, y_pred, target_names=[f"N{label}", label], digits=4))
    return tfidf, clf


class TopLevelClassifier:
    """
    Three independent TF-IDF + LinearSVC binary classifiers.
    Predicts H, Y, B independently — any combination is valid.
    """

    def __init__(self):
        self._models: dict[str, tuple] = {}  # label → (tfidf, clf)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, excel_path: str) -> "TopLevelClassifier":
        df = pd.read_excel(excel_path)
        df["TEXT"] = df["TEXT"].astype(str)
        df["AOD"]  = df["AOD"].astype(str).str.strip()

        for label in LABELS:
            df[f"label_{label}"] = _make_binary(df["AOD"], label)

        print(f"Training on {len(df)} samples")
        print("Label distribution:")
        for label in LABELS:
            pos = df[f"label_{label}"].sum()
            print(f"  {label}: {pos} positive / {len(df) - pos} negative")

        # Single stratified split (stratify on H as most common positive class)
        train_df, val_df = train_test_split(
            df, test_size=0.1, stratify=df["label_H"], random_state=42
        )
        X_train, X_val = train_df["TEXT"].values, val_df["TEXT"].values

        for label in LABELS:
            tfidf, clf = _train_one(
                X_train, train_df[f"label_{label}"].values,
                X_val,   val_df[f"label_{label}"].values,
                label,
            )
            self._models[label] = (tfidf, clf)

        self.save()
        return self

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for label, model in self._models.items():
            joblib.dump(model, MODEL_FILES[label])
            print(f"Saved {MODEL_FILES[label]}")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def load(self) -> "TopLevelClassifier":
        for label in LABELS:
            path = MODEL_FILES[label]
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"Model not found: {path}\n"
                    f"Run: python classifiers/top_level_classifier.py train classifiers/data.xlsx"
                )
            self._models[label] = joblib.load(path)
        return self

    def predict(self, text: str) -> dict[str, int]:
        """Returns {"H": 0|1, "Y": 0|1, "B": 0|1}."""
        if not self._models:
            self.load()
        return {
            label: int(clf.predict(tfidf.transform([text]))[0])
            for label, (tfidf, clf) in self._models.items()
        }


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "train":
        TopLevelClassifier().train(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] != "train":
        result = TopLevelClassifier().predict(sys.argv[1])
        print(result)
    else:
        print("Usage:")
        print("  python classifiers/top_level_classifier.py train classifiers/data.xlsx")
        print("  python classifiers/top_level_classifier.py 'enkaz altında ses var'")
