"""
Method 3 — LLM Classifier (Claude API)

Sends each text to claude-haiku with a Turkish prompt. The model returns
a comma-separated list of category codes. Supports batching to stay within
rate limits and caches results to avoid re-calling on reruns.
"""

import os
import json
import time
from pathlib import Path
from sklearn.model_selection import train_test_split

import anthropic

from utils import load_data, evaluate, CAT_CODES, CATEGORIES

CACHE_PATH = Path(__file__).parent / 'models' / 'llm_cache.json'

SYSTEM_PROMPT = """\
Sen bir afet yardım talep sınıflandırıcısısın. Verilen metni aşağıdaki kategorilerden \
uygun olanlara ata. Birden fazla kategori olabilir.

Kategoriler:
K - Kurtarma (enkaz altında kişi, vinç, kepçe, ekip ihtiyacı)
G - Gıda/Su (yiyecek, içecek, mama, erzak ihtiyacı)
S - Sağlık (tıbbi yardım, ilaç, doktor, ambulans ihtiyacı)
B - Barınma (çadır, konaklama, barınak ihtiyacı)
I - Isıtma (ısıtıcı, battaniye, sobası ihtiyacı)
Y - Giyecek (kıyafet, mont, ayakkabı ihtiyacı)
H - Hijyen (temizlik malzemesi, bez, hijyen paketi ihtiyacı)
U - Ulaşım (araç, taşıma, transfer ihtiyacı)
M - Maddi Destek (para, kişisel ihtiyaç, maddi yardım)
F - Yakıt (mazot, benzin, yakıt ihtiyacı)
N - Yardım Yok (yardım talebi içermiyor, bilgi/haber niteliğinde)

SADECE geçerli kategori kodlarını döndür, virgülle ayır (örnek: K,U veya B,I,Y veya N). \
Başka hiçbir şey yazma.\
"""


def classify_batch(client, texts, model='claude-haiku-4-5-20251001', delay=0.1):
    results = []
    for i, text in enumerate(texts):
        if i > 0 and i % 50 == 0:
            print(f'  ... {i}/{len(texts)} done')

        response = client.messages.create(
            model=model,
            max_tokens=32,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': text[:1000]}],
        )
        raw = response.content[0].text.strip().upper()
        labels = sorted({ch for ch in raw.replace(',', '').replace(' ', '') if ch in CATEGORIES})
        if not labels:
            labels = ['N']
        results.append(labels)

        if delay:
            time.sleep(delay)

    return results


def main():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise EnvironmentError('Set ANTHROPIC_API_KEY environment variable first.')

    print('Loading data...')
    df = load_data()
    print(f'  {len(df)} usable samples')

    _, df_test = train_test_split(df, test_size=0.2, random_state=42)
    X_test = df_test['TEXT'].tolist()
    y_test = df_test['labels'].tolist()
    ids_test = df_test.index.tolist()

    # Load or initialise cache
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text())

    uncached = [(i, idx, X_test[i]) for i, idx in enumerate(ids_test) if str(idx) not in cache]
    print(f'  {len(uncached)} texts not yet cached, calling API...')

    if uncached:
        client = anthropic.Anthropic(api_key=api_key)
        indices, orig_ids, texts = zip(*uncached)
        preds = classify_batch(client, texts)
        for orig_id, pred in zip(orig_ids, preds):
            cache[str(orig_id)] = pred
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        print(f'  Cache saved to {CACHE_PATH}')

    y_pred = [cache.get(str(idx), ['N']) for idx in ids_test]
    evaluate(y_test, y_pred, title='Method 3 — LLM (Claude Haiku)')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    main()
