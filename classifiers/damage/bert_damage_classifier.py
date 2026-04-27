"""
BERT Damage Severity Classifier

Fine-tuned dbmdz/bert-base-turkish-cased model that predicts damage severity:
    AH  — Az Hasar     (minor damage)
    ÇH  — Çok Hasar    (severe damage)
    OH  — Orta Hasar   (moderate damage)
    Y   — Yardım       (not a damage label)
    B   — Bilgi        (not a damage label)
    N   — None         (not a damage label)

Replaces KeywordMatcher for damage severity — same get_matched_keywords interface.
Model lives at data/bert-hasarli-final/ (extracted from bert-hasarli-final.zip).
"""

import torch
from pathlib import Path
from typing import List, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_DIR = str(DATA_DIR / "bert-hasarli-final")
MAX_LEN = 128

DAMAGE_LABELS = {"AH", "ÇH", "OH"}


class BertDamageClassifier:
    """
    Drop-in replacement for KeywordMatcher in the damage severity slot.
    get_matched_keywords() returns a list containing the severity label (e.g. ["ÇH"])
    or an empty list when no damage is detected.
    """

    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._device = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        if not Path(MODEL_DIR).exists():
            raise FileNotFoundError(
                f"BERT damage model not found: {MODEL_DIR}\n"
                f"Extract classifiers/bert-hasarli-final.zip into data/"
            )
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self._device = torch.device("mps")
        else:
            self._device = torch.device("cpu")

        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self._model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
        self._model.to(self._device)
        self._model.eval()

    def predict(self, text: str) -> Optional[str]:
        """Returns severity label (AH/ÇH/OH) if damage detected, else None."""
        self._ensure_loaded()
        enc = self._tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=MAX_LEN,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = self._model(
                enc["input_ids"].to(self._device),
                enc["attention_mask"].to(self._device),
            ).logits
        label_id = int(torch.argmax(logits, dim=-1).item())
        label = self._model.config.id2label[label_id]
        return label if label in DAMAGE_LABELS else None

    def get_matched_keywords(self, text: str) -> List[str]:
        """Compatible with KeywordMatcher interface. Returns [severity] or []."""
        severity = self.predict(text)
        return [severity] if severity else []
