"""
Deprem Verileri Kategorizasyon Sistemi

Bu paket, deprem sonrası Ekşi Sözlük'ten çekilen verileri
10 anahtar kelimeye göre kategorilendirmek için araçlar içerir.
"""

__version__ = "1.0.0"
__author__ = "Kerem"
__description__ = "Deprem Verileri Kategorizasyon Sistemi"

from .text_processor import TurkishTextProcessor, process_text, split_to_sentences, extract_words
from .keyword_matcher import KeywordMatcher, KeywordLoader, create_matcher_from_file, create_matcher_from_list
from .categorize_earthquake_data import EarthquakeDataCategorizer

__all__ = [
    'TurkishTextProcessor',
    'KeywordMatcher',
    'KeywordLoader',
    'EarthquakeDataCategorizer',
    'process_text',
    'split_to_sentences',
    'extract_words',
    'create_matcher_from_file',
    'create_matcher_from_list'
]

