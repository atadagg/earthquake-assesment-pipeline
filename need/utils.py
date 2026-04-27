"""Shared utilities for the need assessment models."""

import re
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    f1_score, precision_score, recall_score, hamming_loss, accuracy_score
)

DATA_PATH = Path(__file__).parent.parent / 'Deprem Yardım (1).xlsx'

CATEGORIES = {
    'K': 'Kurtarma',
    'G': 'Gıda/Su',
    'S': 'Sağlık',
    'B': 'Barınma',
    'I': 'Isıtma',
    'Y': 'Giyecek',
    'H': 'Hijyen',
    'U': 'Ulaşım',
    'M': 'Maddi Destek',
    'F': 'Yakıt',
    'N': 'Yardım Yok',
}

CAT_CODES = list(CATEGORIES.keys())

# Turkish stopwords — domain-specific noise included
STOPWORDS = {
    've', 'bir', 'bu', 'de', 'da', 'için', 'ile', 'olan', 'var', 'çok',
    'gibi', 'ne', 'ise', 'değil', 'mi', 'mı', 'mu', 'mü', 'ki', 'daha',
    'her', 'o', 'ben', 'sen', 'biz', 'siz', 'onlar', 'kadar', 'sonra',
    'önce', 'şu', 'şimdi', 'artık', 'sadece', 'hep', 'bile', 'hem',
    'ya', 'veya', 'ama', 'fakat', 'ancak', 'diye', 'biri', 'bazı',
    'tüm', 'bütün', 'hiç', 'henüz', 'zaten', 'olarak', 'yani',
    'en', 'az', 'fazla', 'tam', 'acil', 'lütfen', 'yok', 'bunlar',
    'şunlar', 'benim', 'senin', 'bizim', 'sizin', 'onun',
    'neden', 'nasıl', 'nereye', 'nereden', 'nerede', 'hangi',
    'oldu', 'olmuş', 'vardı', 'yoktu', 'olup', 'olsa', 'başka',
    'diğer', 'aynı', 'pek', 'edit', 'bkz', 'telefon', 'iletişim',
    'mahallesi', 'caddesi', 'sokak', 'sokağı', 'apartmanı', 'blok',
    'kat', 'daire', 'numara', 'bilgisi', 'olan', 'olan', 'yardım',
    'ihtiyaç', 'lazım', 'gerekiyor', 'gerek', 'gerekli', 'var',
}


def parse_labels(label_str):
    """
    Parse label string to a list of valid category chars.
    Handles all formats: 'GBI', 'G, Y', 'B I', '?K' (uncertain → skip), etc.
    Order is irrelevant — treated as a set.
    """
    if pd.isna(label_str):
        return []
    s = str(label_str).replace(',', '').replace(' ', '').strip()
    if s.startswith('?'):
        return []
    return sorted({ch for ch in s if ch in CATEGORIES})


def preprocess(text):
    if pd.isna(text):
        return ''
    text = str(text).lower()
    # Keep Turkish chars, remove everything else
    text = re.sub(r'[^a-zğüşıöçа-я\s]', ' ', text)
    return ' '.join(text.split())


def tokenize(text, remove_stopwords=True):
    tokens = preprocess(text).split()
    if remove_stopwords:
        tokens = [t for t in tokens if len(t) > 2 and t not in STOPWORDS]
    return tokens


def load_data(label_col='HELP'):
    df = pd.read_excel(DATA_PATH)
    df['labels'] = df[label_col].apply(parse_labels)
    df = df[df['labels'].map(len) > 0].copy()
    df['tokens'] = df['TEXT'].apply(tokenize)
    return df.reset_index(drop=True)


def to_binary(label_lists, cats=CAT_CODES):
    cat_idx = {c: i for i, c in enumerate(cats)}
    mat = np.zeros((len(label_lists), len(cats)), dtype=int)
    for i, labels in enumerate(label_lists):
        for lbl in labels:
            if lbl in cat_idx:
                mat[i, cat_idx[lbl]] = 1
    return mat


def evaluate(y_true_lists, y_pred_lists, title='Results', cats=CAT_CODES):
    y_true = to_binary(y_true_lists, cats)
    y_pred = to_binary(y_pred_lists, cats)

    print(f'\n{"=" * 60}')
    print(f' {title}')
    print(f'{"=" * 60}')
    print(f'  Samples         : {len(y_true)}')
    print(f'  Exact Match Acc : {accuracy_score(y_true, y_pred):.3f}')
    print(f'  Hamming Loss    : {hamming_loss(y_true, y_pred):.3f}')
    print(f'  F1  Micro       : {f1_score(y_true, y_pred, average="micro",  zero_division=0):.3f}')
    print(f'  F1  Macro       : {f1_score(y_true, y_pred, average="macro",  zero_division=0):.3f}')

    print(f'\n  {"Cat":<4} {"Name":<22} {"Prec":>6} {"Rec":>6} {"F1":>6} {"Sup":>5}')
    print(f'  {"-"*50}')
    for i, cat in enumerate(cats):
        p  = precision_score(y_true[:, i], y_pred[:, i], zero_division=0)
        r  = recall_score   (y_true[:, i], y_pred[:, i], zero_division=0)
        f1 = f1_score       (y_true[:, i], y_pred[:, i], zero_division=0)
        sup = int(y_true[:, i].sum())
        print(f'  {cat:<4} {CATEGORIES[cat]:<22} {p:>6.3f} {r:>6.3f} {f1:>6.3f} {sup:>5}')

    return {
        'exact_match': accuracy_score(y_true, y_pred),
        'hamming_loss': hamming_loss(y_true, y_pred),
        'f1_micro': f1_score(y_true, y_pred, average='micro', zero_division=0),
        'f1_macro': f1_score(y_true, y_pred, average='macro', zero_division=0),
    }
