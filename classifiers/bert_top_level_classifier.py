"""
BERT Top-Level Classifier — drop-in replacement for TopLevelClassifier.

Loads three fine-tuned dbmdz/bert-base-turkish-cased models from data/:
    tamDepremBert_H  →  H (Hasar)
    tamDepremBert_Y  →  Y (Yardım)
    tamDepremBert_B  →  B (Bilgi)

Usage:
    clf = BertTopLevelClassifier()
    clf.predict("enkaz altında sesler var")
    → {"H": 1, "Y": 0, "B": 0}
"""

import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

DATA_DIR = Path(__file__).parent.parent / "data"

LABELS = ["H", "Y", "B"]
MODEL_DIRS = {label: str(DATA_DIR / f"tamDepremBert_{label}") for label in LABELS}
MAX_LEN = 128


class BertTopLevelClassifier:
    def __init__(self):
        self._models: dict[str, tuple] = {}  # label → (tokenizer, model)
        self._device = None

    def _get_device(self):
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def load(self) -> "BertTopLevelClassifier":
        self._device = self._get_device()
        for label in LABELS:
            path = MODEL_DIRS[label]
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"BERT model not found: {path}\n"
                    f"Download tamDepremBert_{label} from Colab and place in data/"
                )
            tokenizer = AutoTokenizer.from_pretrained(path)
            model = AutoModelForSequenceClassification.from_pretrained(path)
            model.to(self._device)
            model.eval()
            self._models[label] = (tokenizer, model)
        return self

    def predict(self, text: str) -> dict[str, int]:
        """Returns {"H": 0|1, "Y": 0|1, "B": 0|1}."""
        if not self._models:
            self.load()
        results = {}
        for label, (tokenizer, model) in self._models.items():
            enc = tokenizer(
                text,
                truncation=True,
                padding="max_length",
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = model(
                    enc["input_ids"].to(self._device),
                    enc["attention_mask"].to(self._device),
                ).logits
            pred = int(torch.argmax(logits, dim=-1).item())
            results[label] = pred
        return results
