"""
Method 1 — Top-10 Words per Category

For each category, collect training texts, count word frequencies (stopwords
removed), take the top-10 most frequent words. At inference, count how many
of a category's top-10 words appear in the text and assign all categories
with at least one match. If nothing matches, fall back to the category with
the highest raw count.
"""

from collections import Counter
from sklearn.model_selection import train_test_split

from utils import load_data, evaluate, CAT_CODES, tokenize, CATEGORIES


class TopWordsClassifier:
    def __init__(self, top_n=10, threshold=1):
        self.top_n = top_n
        self.threshold = threshold
        self.profiles = {}   # cat → list of top words

    def fit(self, texts, label_lists):
        cat_tokens = {c: [] for c in CAT_CODES}
        for tokens, labels in zip(texts, label_lists):
            for lbl in labels:
                if lbl in cat_tokens:
                    cat_tokens[lbl].extend(tokens)

        self.profiles = {}
        for cat, tokens in cat_tokens.items():
            counts = Counter(tokens)
            self.profiles[cat] = [w for w, _ in counts.most_common(self.top_n)]

        return self

    def predict_one(self, tokens):
        token_set = set(tokens)
        scores = {}
        for cat, words in self.profiles.items():
            scores[cat] = sum(1 for w in words if w in token_set)

        predicted = [c for c, s in scores.items() if s >= self.threshold]

        # fallback: if nothing matched, take argmax
        if not predicted:
            best = max(scores, key=scores.get)
            predicted = [best]

        return predicted

    def predict(self, texts):
        return [self.predict_one(tokenize(t)) for t in texts]

    def print_profiles(self):
        print('\nTop words per category:')
        for cat in CAT_CODES:
            words = self.profiles.get(cat, [])
            print(f'  {cat} ({CATEGORIES[cat]:<22}): {", ".join(words)}')


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

    clf = TopWordsClassifier(top_n=10, threshold=1)
    clf.fit(tok_train, y_train)
    clf.print_profiles()

    y_pred = clf.predict(X_test)
    evaluate(y_test, y_pred, title='Method 1 — Top-10 Words')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
    main()
