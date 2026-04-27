"""
Method 2 — BM25 Classifier

For each category a "super-document" is built from all training texts with
that label. At inference, BM25 scores the query (test text tokens) against
every category super-document. Categories whose normalised score exceeds a
threshold are predicted; if none pass, the top-scoring category is returned.
"""

from rank_bm25 import BM25Okapi
from sklearn.model_selection import train_test_split

from utils import load_data, evaluate, CAT_CODES, tokenize, CATEGORIES


class BM25Classifier:
    def __init__(self, threshold=0.0):
        """threshold: fraction of max score a category must reach (0 → always pick at least one)."""
        self.threshold = threshold
        self.bm25 = None
        self.cats_order = []

    def fit(self, texts, label_lists):
        cat_tokens = {c: [] for c in CAT_CODES}
        for tokens, labels in zip(texts, label_lists):
            for lbl in labels:
                if lbl in cat_tokens:
                    cat_tokens[lbl].extend(tokens)

        # One document per category (super-document of all tokens)
        self.cats_order = [c for c in CAT_CODES if cat_tokens[c]]
        self._cat_tokens = {c: cat_tokens[c] for c in self.cats_order}
        corpus = [cat_tokens[c] for c in self.cats_order]
        self.bm25 = BM25Okapi(corpus)
        return self

    def predict_one(self, tokens):
        scores = self.bm25.get_scores(tokens)
        max_score = max(scores) if max(scores) > 0 else 1.0

        predicted = [
            self.cats_order[i]
            for i, s in enumerate(scores)
            if s / max_score >= self.threshold
        ]

        # fallback
        if not predicted:
            predicted = [self.cats_order[int(scores.argmax())]]

        return predicted

    def predict(self, texts):
        return [self.predict_one(tokenize(t)) for t in texts]

    def print_top_terms(self, top_n=10):
        """Show the top-N terms BM25 weights highest for each category."""
        print('\nTop BM25 terms per category (by IDF weight):')
        import numpy as np
        idf = self.bm25.idf
        vocab = list(self.bm25.corpus_size * [None])  # placeholder

        # rank_bm25 doesn't directly expose vocab; show raw IDF ordering
        for i, cat in enumerate(self.cats_order):
            unique = list(set(self._cat_tokens[cat]))
            word_scores = [(w, self.bm25.get_scores([w])[i]) for w in unique]
            word_scores.sort(key=lambda x: -x[1])
            top_words = [w for w, _ in word_scores[:top_n]]
            print(f'  {cat} ({CATEGORIES[cat]:<22}): {", ".join(top_words)}')


def main():
    print('Loading data...')
    df = load_data()
    print(f'  {len(df)} usable samples')

    X = df['TEXT'].tolist()
    y = df['labels'].tolist()
    tok = df['tokens'].tolist()

    X_train, X_test, tok_train, tok_test, y_train, y_test = train_test_split(
        X, tok, y, test_size=0.2, random_state=42
    )

    clf = BM25Classifier(threshold=0.5)
    clf.fit(tok_train, y_train)
    clf.print_top_terms()

    y_pred = clf.predict(X_test)
    evaluate(y_test, y_pred, title='Method 2 — BM25')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
    main()
