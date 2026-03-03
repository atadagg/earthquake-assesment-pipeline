"""
Top-Level Classifier — Python port of CS401/WekaManager.java

Classifies earthquake-related text into:
    H   — Hasar      (damage only)
    Y   — Yardım     (need/help only)
    HY  — Both damage and need
    B   — Other / background

Training:   TopLevelClassifier().train("path/to/data.xlsx")
Inference:  TopLevelClassifier().predict("enkaz altında sesler var")

Label merging (matches Java logic):
    HYB → HY
    HB  → H
    YB  → Y
"""

import re
import joblib
import openpyxl
from pathlib import Path
from typing import Optional

from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer

CATEGORIES = ["H", "Y", "HY", "B"]
MODEL_FILE = str(Path(__file__).parent.parent / "data" / "toplevel_model.joblib")

_LABEL_MAP = {
    "HYB": "HY",
    "HB":  "H",
    "YB":  "Y",
}

# Initialised once at module load — mirrors MorphologyHelper.init()
_analyzer = FsmMorphologicalAnalyzer()


def _normalize_label(label: str) -> Optional[str]:
    label = label.strip()
    label = _LABEL_MAP.get(label, label)
    return label if label in CATEGORIES else None


def _turkish_lower(text: str) -> str:
    """Locale-aware Turkish lowercase (İ→i, I→ı)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _analyze_word(word: str) -> str:
    """
    Return the longest root for a single word.
    Direct port of MorphologyHelper.analyzeWord().
    """
    try:
        parses = _analyzer.morphologicalAnalysis(word)
        if parses is None or parses.size() == 0:
            return word
        best_root = ""
        max_len = -1
        for i in range(parses.size()):
            parse = parses.getFsmParse(i)
            current_root = parse.transitionList().split("+")[0]
            if len(current_root) > max_len:
                max_len = len(current_root)
                best_root = current_root
        return best_root if best_root else word
    except Exception:
        return word


def _extract_roots(text: str) -> str:
    """
    Strip Turkish suffixes and return a string of roots.
    Direct port of MorphologyHelper.extractRoots().
    """
    clean = re.sub(r"[^a-zA-ZçğıöşüÇĞİÖŞÜ\s]", " ", text)
    words = clean.split()
    result = []
    for w in words:
        if len(w) < 2:
            continue
        root = _analyze_word(_turkish_lower(w))
        result.append(root)
    return " ".join(result)


class TopLevelClassifier:
    """
    TF-IDF + Multinomial Naive Bayes classifier.
    Scikit-learn port of WekaManager.java.
    """

    def __init__(self, model_file: str = MODEL_FILE):
        self.model_file = model_file
        self._pipeline: Optional[Pipeline] = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, excel_path: str) -> "TopLevelClassifier":
        """
        Train from an Excel file (col 0: raw text, col 1: label).
        Saves the fitted model to model_file.
        """
        texts, labels = self._load_excel(excel_path)
        if not texts:
            raise ValueError(f"No usable training rows found in {excel_path}")

        print(f"Training on {len(texts)} samples...")
        processed = [_extract_roots(t) for t in texts]

        # TF-IDF + Naive Bayes — mirrors StringToWordVector + NaiveBayesMultinomial
        self._pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                sublinear_tf=True,   # log(tf)+1  ≈ Weka TF transform
                use_idf=True,
                lowercase=False,     # already lowercased in _extract_roots
                ngram_range=(1, 2),
                min_df=2,
                max_features=20_000,
            )),
            ("clf", MultinomialNB()),
        ])
        self._pipeline.fit(processed, labels)

        Path(self.model_file).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._pipeline, self.model_file)
        print(f"Model saved: {self.model_file}")
        return self

    def _load_excel(self, excel_path: str):
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        ws = wb.active
        texts, labels = [], []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # skip header
            if not row or len(row) < 2 or row[0] is None or row[1] is None:
                continue
            label = _normalize_label(str(row[1]))
            if label is None:
                continue
            texts.append(str(row[0]))
            labels.append(label)
        wb.close()
        return texts, labels

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def load(self) -> "TopLevelClassifier":
        """Load a previously saved model from disk."""
        if not Path(self.model_file).exists():
            raise FileNotFoundError(
                f"Model not found: {self.model_file}\n"
                f"Run: python classifiers/top_level_classifier.py train <data.xlsx>"
            )
        self._pipeline = joblib.load(self.model_file)
        return self

    def predict(self, text: str) -> str:
        """
        Predict the top-level category for a single text.
        Returns one of: 'H', 'Y', 'HY', 'B'
        Auto-loads the saved model if not already loaded.
        """
        if self._pipeline is None:
            self.load()
        return self._pipeline.predict([_extract_roots(text)])[0]

    def predict_proba(self, text: str) -> dict:
        """Return class probabilities as {category: probability}."""
        if self._pipeline is None:
            self.load()
        probs = self._pipeline.predict_proba([_extract_roots(text)])[0]
        return dict(zip(self._pipeline.classes_, probs))


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "train":
        TopLevelClassifier().train(sys.argv[2])
    elif len(sys.argv) == 2:
        print(f"Category: {TopLevelClassifier().predict(sys.argv[1])}")
    else:
        print("Usage:")
        print("  python top_level_classifier.py train data.xlsx")
        print("  python top_level_classifier.py 'enkaz altında ses var'")
