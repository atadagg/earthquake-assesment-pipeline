#!/usr/bin/env python3
"""
Multi-Label Text Classification using Keyword Heuristics
This version loads keywords from an external file for easy editing.

Categories: K, G, S, B, I, Y, H, U, M, F
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import hamming_loss
import re
from pathlib import Path


class KeywordClassifier:
    """
    Multi-label classifier using keyword matching.
    Keywords are loaded from an external file for easy manual editing.
    """

    def __init__(self, keywords_file, threshold=2):
        """
        Initialize the classifier.

        Args:
            keywords_file: Path to the keywords configuration file
            threshold: Minimum number of keywords that must match to predict a category
        """
        self.keywords_file = keywords_file
        self.threshold = threshold
        self.category_keywords = {}
        self.categories = []
        self.load_keywords()

    def load_keywords(self):
        """Load keywords from the configuration file."""
        print(f"\nLoading keywords from: {self.keywords_file}")

        if not Path(self.keywords_file).exists():
            raise FileNotFoundError(f"Keywords file not found: {self.keywords_file}")

        with open(self.keywords_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse: CATEGORY | keyword1, keyword2, ...
                if '|' not in line:
                    continue

                category, keywords_str = line.split('|', 1)
                category = category.strip()
                keywords = [kw.strip() for kw in keywords_str.split(',')]

                self.category_keywords[category] = keywords
                self.categories.append(category)

        print(f"Loaded {len(self.categories)} categories")
        for cat, keywords in self.category_keywords.items():
            print(f"  {cat}: {len(keywords)} keywords - {', '.join(keywords[:5])}...")

    def preprocess_text(self, text):
        """Basic text preprocessing."""
        if pd.isna(text):
            return ""
        # Convert to lowercase
        text = str(text).lower()
        # Remove special characters but keep Turkish characters
        text = re.sub(r'[^a-zğüşıöçİĞÜŞÖÇ\s]', ' ', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def predict_single(self, text):
        """
        Predict categories for a single text.

        Args:
            text: Input text

        Returns:
            List of predicted categories with match counts
        """
        processed_text = self.preprocess_text(text)
        predictions = []

        # Check each category's keywords
        for category, keywords in self.category_keywords.items():
            # Count how many keywords are present in the text
            matched_keywords = [kw for kw in keywords if kw in processed_text]
            keyword_count = len(matched_keywords)

            # Only predict if at least 'threshold' keywords are present
            if keyword_count >= self.threshold:
                predictions.append({
                    'category': category,
                    'matches': keyword_count,
                    'matched_keywords': matched_keywords
                })

        # Sort by number of matches (descending)
        predictions.sort(key=lambda x: x['matches'], reverse=True)

        return predictions

    def predict(self, X, return_details=False):
        """
        Predict categories for multiple texts.

        Args:
            X: List of text documents
            return_details: If True, return detailed match information

        Returns:
            List of predicted label sets (or detailed predictions if return_details=True)
        """
        if return_details:
            return [self.predict_single(text) for text in X]
        else:
            return [[p['category'] for p in self.predict_single(text)] for text in X]


def load_and_prepare_data(file_path):
    """
    Load data from Excel and prepare for evaluation.

    Returns:
        X: List of texts
        y: List of label sets
        df: Original dataframe
    """
    print(f"Loading data from {file_path}...")
    df = pd.read_excel(file_path)

    # Filter out rows with missing GPT HELP
    df_clean = df[df['GPT HELP'].notna()].copy()
    print(f"Loaded {len(df_clean)} samples (removed {len(df) - len(df_clean)} with missing labels)")

    # Extract texts
    X = df_clean['TEXT'].tolist()

    # Parse labels (handle multi-label format like "K, G, S")
    y = []
    for label_str in df_clean['GPT HELP']:
        # Split by comma and clean
        labels = [l.strip() for l in str(label_str).split(',')]
        y.append(labels)

    return X, y, df_clean


def evaluate_multilabel(y_true, y_pred, categories):
    """
    Evaluate multi-label classification performance.

    Args:
        y_true: List of true label sets
        y_pred: List of predicted label sets
        categories: List of all possible categories

    Returns:
        Dictionary of evaluation metrics
    """
    # Convert to binary format for sklearn metrics
    n_samples = len(y_true)
    n_categories = len(categories)

    y_true_binary = np.zeros((n_samples, n_categories), dtype=int)
    y_pred_binary = np.zeros((n_samples, n_categories), dtype=int)

    category_to_idx = {cat: i for i, cat in enumerate(categories)}

    for i in range(n_samples):
        for cat in y_true[i]:
            if cat in category_to_idx:
                y_true_binary[i, category_to_idx[cat]] = 1
        for cat in y_pred[i]:
            if cat in category_to_idx:
                y_pred_binary[i, category_to_idx[cat]] = 1

    # Calculate metrics
    metrics = {
        'hamming_loss': hamming_loss(y_true_binary, y_pred_binary),
        'exact_match_ratio': accuracy_score(y_true_binary, y_pred_binary),
        'precision_micro': precision_score(y_true_binary, y_pred_binary, average='micro', zero_division=0),
        'recall_micro': recall_score(y_true_binary, y_pred_binary, average='micro', zero_division=0),
        'f1_micro': f1_score(y_true_binary, y_pred_binary, average='micro', zero_division=0),
        'precision_macro': precision_score(y_true_binary, y_pred_binary, average='macro', zero_division=0),
        'recall_macro': recall_score(y_true_binary, y_pred_binary, average='macro', zero_division=0),
        'f1_macro': f1_score(y_true_binary, y_pred_binary, average='macro', zero_division=0),
    }

    # Per-category metrics
    print("\nPer-Category Performance:")
    print("-" * 70)
    print(f"{'Category':<10} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support'}")
    print("-" * 70)

    for i, cat in enumerate(categories):
        precision = precision_score(y_true_binary[:, i], y_pred_binary[:, i], zero_division=0)
        recall = recall_score(y_true_binary[:, i], y_pred_binary[:, i], zero_division=0)
        f1 = f1_score(y_true_binary[:, i], y_pred_binary[:, i], zero_division=0)
        support = y_true_binary[:, i].sum()

        print(f"{cat:<10} {precision:<12.3f} {recall:<12.3f} {f1:<12.3f} {support}")

    return metrics


def main():
    """Main execution function."""

    # Configuration
    file_path = "Deprem Yardım.xlsx"
    keywords_file = "category_keywords.txt"
    test_size = 0.2
    random_state = 42
    threshold = 1  # Minimum keywords required to predict a category

    print("=" * 70)
    print("Keyword-Based Multi-Label Text Classifier (v2)")
    print("=" * 70)

    # Load data
    X, y, df = load_and_prepare_data(file_path)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Create classifier
    print("\n" + "=" * 70)
    print("Loading Classifier")
    print("=" * 70)
    print(f"Configuration: threshold={threshold} (min keywords to match)")

    classifier = KeywordClassifier(keywords_file=keywords_file, threshold=threshold)

    # Predict on test set
    print("\n" + "=" * 70)
    print("Predicting on Test Set")
    print("=" * 70)

    y_pred = classifier.predict(X_test)

    # Evaluate
    print("\n" + "=" * 70)
    print("Evaluation Results")
    print("=" * 70)

    metrics = evaluate_multilabel(y_test, y_pred, classifier.categories)

    print("\nOverall Metrics:")
    print("-" * 70)
    print(f"Exact Match Ratio (Accuracy): {metrics['exact_match_ratio']:.3f}")
    print(f"Hamming Loss: {metrics['hamming_loss']:.3f}")
    print(f"\nMicro-averaged (overall performance):")
    print(f"  Precision: {metrics['precision_micro']:.3f}")
    print(f"  Recall:    {metrics['recall_micro']:.3f}")
    print(f"  F1-Score:  {metrics['f1_micro']:.3f}")
    print(f"\nMacro-averaged (per-category average):")
    print(f"  Precision: {metrics['precision_macro']:.3f}")
    print(f"  Recall:    {metrics['recall_macro']:.3f}")
    print(f"  F1-Score:  {metrics['f1_macro']:.3f}")

    # Show some examples with details
    print("\n" + "=" * 70)
    print("Sample Predictions (first 10 test samples with match details)")
    print("=" * 70)

    y_pred_detailed = classifier.predict(X_test[:10], return_details=True)

    for i in range(10):
        print(f"\n[{i+1}] Text: {X_test[i][:100]}...")
        print(f"    True labels: {', '.join(y_test[i]) if y_test[i] else 'None'}")

        if y_pred_detailed[i]:
            print(f"    Predictions:")
            for pred in y_pred_detailed[i]:
                print(f"      - {pred['category']} ({pred['matches']} matches): {', '.join(pred['matched_keywords'][:5])}")
        else:
            print(f"    Predictions: None")

        match = set(y_test[i]) == set([p['category'] for p in y_pred_detailed[i]])
        print(f"    Exact match: {'✓ YES' if match else '✗ NO'}")

    print("\n" + "=" * 70)
    print("TIP: Edit 'category_keywords.txt' to improve results!")
    print("=" * 70)


if __name__ == "__main__":
    main()
