"""
Damage keyword utilities used by the main pipeline.

Runtime uses:
- KeywordLoader.load_from_file("classifiers/damage/keywords.txt")
- KeywordMatcher(...).get_matched_keywords(text)
"""

from .keyword_matcher import KeywordMatcher, KeywordLoader
from .text_processor import TurkishTextProcessor

__all__ = [
    "TurkishTextProcessor",
    "KeywordMatcher",
    "KeywordLoader",
]

