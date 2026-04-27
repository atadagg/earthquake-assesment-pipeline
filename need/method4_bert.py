"""
Method 4 — Fine-tuned Turkish BERT

Multi-label classification on top of dbmdz/bert-base-turkish-cased.
Adds a linear classification head with BCEWithLogitsLoss.
Saves the best checkpoint to need/models/bert/.
"""

import sys
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent))
from utils import load_data, evaluate, CAT_CODES, to_binary, CATEGORIES

MODEL_NAME = 'dbmdz/bert-base-turkish-cased'
SAVE_PATH  = Path(__file__).parent / 'models' / 'bert'
MAX_LEN    = 128
BATCH_SIZE = 16
EPOCHS     = 5
LR         = 2e-5
THRESHOLD  = 0.5


def p(*args, **kwargs):
    """Print with immediate flush."""
    print(*args, **kwargs, flush=True)


class NeedDataset(Dataset):
    """Tokenizes lazily per sample — avoids blocking on the full corpus upfront."""

    def __init__(self, texts, labels, tokenizer):
        self.texts     = texts
        self.labels    = torch.tensor(labels, dtype=torch.float)
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            padding='max_length',
            truncation=True,
            max_length=MAX_LEN,
            return_tensors='pt',
        )
        return {
            'input_ids':      enc['input_ids'].squeeze(0),
            'attention_mask': enc['attention_mask'].squeeze(0),
            'labels':         self.labels[idx],
        }


class BertNeedClassifier(nn.Module):
    def __init__(self, n_labels, model_name=MODEL_NAME):
        super().__init__()
        self.bert   = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        self.drop   = nn.Dropout(0.1)
        self.head   = nn.Linear(hidden_size, n_labels)

    def forward(self, input_ids, attention_mask):
        out    = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = out.last_hidden_state[:, 0, :]   # [CLS] token
        return self.head(self.drop(pooled))


def train_epoch(model, loader, optimizer, scheduler, device):
    model.train()
    criterion  = nn.BCEWithLogitsLoss()
    total_loss = 0.0
    for i, batch in enumerate(loader):
        optimizer.zero_grad()
        logits = model(
            batch['input_ids'].to(device),
            batch['attention_mask'].to(device),
        )
        loss = criterion(logits, batch['labels'].to(device))
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        total_loss += loss.item()
        if (i + 1) % 20 == 0:
            p(f'    batch {i+1}/{len(loader)}  loss={total_loss/(i+1):.4f}')
    return total_loss / len(loader)


@torch.no_grad()
def eval_epoch(model, loader, device):
    model.eval()
    all_logits, all_labels = [], []
    for batch in loader:
        logits = model(
            batch['input_ids'].to(device),
            batch['attention_mask'].to(device),
        )
        all_logits.append(logits.cpu())
        all_labels.append(batch['labels'].cpu())
    logits = torch.cat(all_logits)
    labels = torch.cat(all_labels)
    preds  = (torch.sigmoid(logits) >= THRESHOLD).int().numpy()
    from sklearn.metrics import f1_score
    return f1_score(labels.int().numpy(), preds, average='micro', zero_division=0)


def preds_to_label_lists(binary_preds):
    return [
        [CAT_CODES[j] for j in range(len(CAT_CODES)) if row[j] == 1] or ['N']
        for row in binary_preds
    ]


def main():
    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')
    p(f'Device: {device}')

    p('Loading data...')
    df = load_data()
    p(f'  {len(df)} usable samples')

    texts  = df['TEXT'].tolist()
    labels = df['labels'].tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.1, random_state=42
    )

    y_train_bin = to_binary(y_train)
    y_val_bin   = to_binary(y_val)
    y_test_bin  = to_binary(y_test)

    p(f'  Train {len(X_train)} | Val {len(X_val)} | Test {len(X_test)}')

    p('Loading tokenizer...')
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    p('  tokenizer ready')

    train_ds = NeedDataset(X_train, y_train_bin, tokenizer)
    val_ds   = NeedDataset(X_val,   y_val_bin,   tokenizer)
    test_ds  = NeedDataset(X_test,  y_test_bin,  tokenizer)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, num_workers=0)

    p('Loading BERT model...')
    model     = BertNeedClassifier(n_labels=len(CAT_CODES)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps,
    )
    p(f'  model ready — {total_steps} total steps')

    best_val_f1 = 0.0
    SAVE_PATH.mkdir(parents=True, exist_ok=True)

    p('\nTraining...')
    for epoch in range(1, EPOCHS + 1):
        p(f'\n--- Epoch {epoch}/{EPOCHS} ---')
        loss   = train_epoch(model, train_loader, optimizer, scheduler, device)
        val_f1 = eval_epoch(model, val_loader, device)
        p(f'  => loss={loss:.4f}  val_f1={val_f1:.4f}', end='  ')

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            torch.save(model.state_dict(), SAVE_PATH / 'best_model.pt')
            tokenizer.save_pretrained(SAVE_PATH)
            p('checkpoint saved')
        else:
            p('')

    p('\nEvaluating best checkpoint on test set...')
    model.load_state_dict(torch.load(SAVE_PATH / 'best_model.pt', map_location=device))
    model.eval()
    all_logits = []
    with torch.no_grad():
        for batch in test_loader:
            logits = model(
                batch['input_ids'].to(device),
                batch['attention_mask'].to(device),
            )
            all_logits.append(logits.cpu())
    logits    = torch.cat(all_logits)
    bin_preds = (torch.sigmoid(logits) >= THRESHOLD).int().numpy()

    y_pred = preds_to_label_lists(bin_preds)
    evaluate(y_test, y_pred, title=f'Method 4 — BERT ({MODEL_NAME})')
    p(f'\nModel saved to: {SAVE_PATH}')


class BertNeedsClassifier:
    """
    Drop-in replacement for KeywordClassifier.
    Loads the trained BertNeedClassifier checkpoint and exposes predict_single().
    """

    def __init__(self, model_dir: str | None = None):
        if model_dir is None:
            model_dir = str(SAVE_PATH)
        self._model_dir = Path(model_dir)
        self._model = None
        self._tokenizer = None
        self._device = None

    def _load(self):
        if torch.cuda.is_available():
            self._device = torch.device('cuda')
        elif torch.backends.mps.is_available():
            self._device = torch.device('mps')
        else:
            self._device = torch.device('cpu')

        self._tokenizer = AutoTokenizer.from_pretrained(str(self._model_dir))
        self._model = BertNeedClassifier(n_labels=len(CAT_CODES)).to(self._device)
        self._model.load_state_dict(
            torch.load(str(self._model_dir / 'best_model.pt'), map_location=self._device)
        )
        self._model.eval()

    def predict_single(self, text: str) -> list[dict]:
        """Returns [{"category": "K"}, ...] — same shape as KeywordClassifier."""
        if self._model is None:
            self._load()

        enc = self._tokenizer(
            text,
            padding='max_length',
            truncation=True,
            max_length=MAX_LEN,
            return_tensors='pt',
        )
        with torch.no_grad():
            logits = self._model(
                enc['input_ids'].to(self._device),
                enc['attention_mask'].to(self._device),
            )
        probs = torch.sigmoid(logits).squeeze(0).cpu().numpy()
        predicted = [CAT_CODES[i] for i, p in enumerate(probs) if p >= THRESHOLD]
        if not predicted:
            predicted = ['N']
        return [{'category': cat} for cat in predicted]


if __name__ == '__main__':
    main()
