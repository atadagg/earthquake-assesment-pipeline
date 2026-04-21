"""
Anahtar Kelime Eşleştirme Modülü
10 anahtar kelimeye göre metinleri kategorilendirme işlemlerini yapar.
"""

import re
from collections import Counter
from typing import Any, List, Dict, Set, Tuple
from .text_processor import TurkishTextProcessor


class KeywordMatcher:
    """Anahtar kelime eşleştirme ve kategorizasyon sınıfı"""
    
    def __init__(self, keywords: List[str]):
        """
        Anahtar kelime eşleştiricisi başlatıcı
        
        Args:
            keywords: 10 anahtar kelime listesi
        """
        self.keywords = keywords
        self.processor = TurkishTextProcessor()
        
        # Kelimeleri normalize et
        self.normalized_keywords = [
            self.processor.turkish_lower(kw.strip()) for kw in keywords
        ]
    
    def match_keywords(self, text: str) -> Dict[str, bool]:
        """
        Metinde hangi anahtar kelimelerin geçtiğini bulur
        
        Args:
            text: Analiz edilecek metin
            
        Returns:
            Anahtar kelime: Boolean (var/yok) sözlüğü
        """
        # Metni normalize et
        normalized_text = self.processor.turkish_lower(text)
        
        # Her anahtar kelime için kontrol
        matches = {}
        for i, keyword in enumerate(self.normalized_keywords):
            # Kelime sınırları ile eşleştir
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches[self.keywords[i]] = bool(re.search(pattern, normalized_text))
        
        return matches
    
    def match_keywords_with_count(self, text: str) -> Dict[str, int]:
        """
        Metinde anahtar kelimelerin kaç kez geçtiğini sayar
        
        Args:
            text: Analiz edilecek metin
            
        Returns:
            Anahtar kelime: Frekans sözlüğü
        """
        # Metni normalize et
        normalized_text = self.processor.turkish_lower(text)
        
        # Her anahtar kelime için say
        counts = {}
        for i, keyword in enumerate(self.normalized_keywords):
            # Kelime sınırları ile eşleştir ve say
            pattern = r'\b' + re.escape(keyword) + r'\b'
            count = len(re.findall(pattern, normalized_text))
            counts[self.keywords[i]] = count
        
        return counts
    
    def get_matched_keywords(self, text: str) -> List[str]:
        """
        Metinde geçen anahtar kelimeleri liste olarak döndürür
        
        Args:
            text: Analiz edilecek metin
            
        Returns:
            Eşleşen anahtar kelime listesi
        """
        matches = self.match_keywords(text)
        return [kw for kw, matched in matches.items() if matched]
    
    def categorize_text(self, text: str) -> Dict[str, Any]:
        """
        Metni kategorilere ayırır ve detaylı bilgi döndürür
        
        Args:
            text: Kategorize edilecek metin
            
        Returns:
            Kategorizasyon sonuçları
        """
        # Anahtar kelime eşleşmeleri
        matches = self.match_keywords(text)
        counts = self.match_keywords_with_count(text)
        matched_keywords = self.get_matched_keywords(text)
        
        # Sonuçları oluştur
        result = {
            'text': text,
            'matched_keywords': matched_keywords,
            'keyword_count': len(matched_keywords),
            'total_matches': sum(counts.values()),
            'keyword_frequencies': counts,
            'keyword_presence': matches,
            'categories': self._assign_categories(matched_keywords)
        }
        
        return result
    
    def _assign_categories(self, matched_keywords: List[str]) -> List[str]:
        """
        Eşleşen anahtar kelimelere göre kategori atar
        
        Args:
            matched_keywords: Eşleşen anahtar kelimeler
            
        Returns:
            Kategori listesi
        """
        # Her anahtar kelime bir kategori olarak kabul edilir
        # İlerleye dönük: Kelimeleri gruplandırabilirsiniz
        return matched_keywords.copy()
    
    def categorize_multiple_texts(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Birden fazla metni kategorize eder
        
        Args:
            texts: Metin listesi
            
        Returns:
            Kategorizasyon sonuçları listesi
        """
        results = []
        for text in texts:
            result = self.categorize_text(text)
            results.append(result)
        
        return results
    
    def get_statistics(self, texts: List[str]) -> Dict[str, Any]:
        """
        Metinler üzerinde kategorizasyon istatistikleri üretir
        
        Args:
            texts: Analiz edilecek metin listesi
            
        Returns:
            İstatistiksel sonuçlar
        """
        # Tüm metinleri kategorize et
        results = self.categorize_multiple_texts(texts)
        
        # İstatistikleri topla
        total_texts = len(texts)
        keyword_counter = Counter()
        total_matches = 0
        texts_with_matches = 0
        
        for result in results:
            if result['keyword_count'] > 0:
                texts_with_matches += 1
            
            total_matches += result['total_matches']
            
            for keyword, count in result['keyword_frequencies'].items():
                if count > 0:
                    keyword_counter[keyword] += 1
        
        # İstatistik sözlüğü
        statistics = {
            'total_texts': total_texts,
            'texts_with_matches': texts_with_matches,
            'texts_without_matches': total_texts - texts_with_matches,
            'match_rate': (texts_with_matches / total_texts * 100) if total_texts > 0 else 0,
            'total_keyword_occurrences': total_matches,
            'avg_keywords_per_text': total_matches / total_texts if total_texts > 0 else 0,
            'keyword_distribution': dict(keyword_counter),
            'keyword_percentages': {
                kw: (count / total_texts * 100) 
                for kw, count in keyword_counter.items()
            }
        }
        
        return statistics


class KeywordLoader:
    """Anahtar kelimeleri dosyadan yükler"""
    
    @staticmethod
    def load_from_file(filename: str) -> List[str]:
        """
        Dosyadan anahtar kelimeleri yükler
        
        Args:
            filename: Anahtar kelime dosyası yolu
            
        Returns:
            Anahtar kelime listesi
        """
        keywords = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    keyword = line.strip()
                    if keyword and not keyword.startswith('#'):
                        keywords.append(keyword)
        except FileNotFoundError:
            print(f"Uyarı: {filename} bulunamadı")
        
        return keywords
    
    @staticmethod
    def load_from_list(keyword_list: List[str]) -> List[str]:
        """
        Liste olarak verilen anahtar kelimeleri döndürür
        
        Args:
            keyword_list: Anahtar kelime listesi
            
        Returns:
            Temizlenmiş anahtar kelime listesi
        """
        return [kw.strip() for kw in keyword_list if kw.strip()]
    
    @staticmethod
    def save_to_file(keywords: List[str], filename: str):
        """
        Anahtar kelimeleri dosyaya kaydeder
        
        Args:
            keywords: Anahtar kelime listesi
            filename: Kayıt edilecek dosya yolu
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Deprem Verileri Kategorizasyon - Anahtar Kelimeler\n")
            f.write("# Her satırda bir anahtar kelime\n\n")
            for keyword in keywords:
                f.write(f"{keyword}\n")


# Utility fonksiyonları
def create_matcher_from_file(keywords_file: str) -> KeywordMatcher:
    """
    Dosyadan anahtar kelime eşleştirici oluşturur
    
    Args:
        keywords_file: Anahtar kelime dosyası yolu
        
    Returns:
        KeywordMatcher nesnesi
    """
    keywords = KeywordLoader.load_from_file(keywords_file)
    return KeywordMatcher(keywords)


def create_matcher_from_list(keywords: List[str]) -> KeywordMatcher:
    """
    Listeden anahtar kelime eşleştirici oluşturur
    
    Args:
        keywords: Anahtar kelime listesi
        
    Returns:
        KeywordMatcher nesnesi
    """
    return KeywordMatcher(keywords)


# Test için
if __name__ == "__main__":
    # Test anahtar kelimeleri
    test_keywords = [
        "deprem", "afet", "yardım", "enkaz", "kurtarma",
        "yıkım", "kayıp", "hastane", "barınak", "koordinasyon"
    ]
    
    # Matcher oluştur
    matcher = KeywordMatcher(test_keywords)
    
    # Test metni
    test_text = """
    Deprem sonrasında enkaz altında kalan insanların kurtarma çalışmaları devam ediyor.
    Yardım malzemeleri bölgeye ulaştırılıyor. Hastanelerde yaralıların tedavisi sürüyor.
    """
    
    print("Test Metni:", test_text)
    print("\n" + "="*50)
    
    # Kategorizasyon
    result = matcher.categorize_text(test_text)
    
    print("\nEşleşen Anahtar Kelimeler:", result['matched_keywords'])
    print("Toplam Eşleşme:", result['keyword_count'])
    print("Kelime Frekansları:", result['keyword_frequencies'])
    
    # Çoklu metin testi
    test_texts = [
        "Deprem bölgesinde enkaz kaldırma çalışmaları sürüyor.",
        "Yardım kampanyaları düzenleniyor.",
        "Bu metin anahtar kelime içermiyor."
    ]
    
    print("\n" + "="*50)
    print("\nÇoklu Metin İstatistikleri:")
    stats = matcher.get_statistics(test_texts)
    
    print(f"Toplam Metin: {stats['total_texts']}")
    print(f"Eşleşme Oranı: {stats['match_rate']:.2f}%")
    print(f"Kelime Dağılımı: {stats['keyword_distribution']}")

