"""
Metin İşleme Modülü
Türkçe metinleri işlemek için gerekli fonksiyonları içerir.
"""

import re
from typing import List, Dict

class TurkishTextProcessor:
    """Türkçe metinleri işlemek için araç sınıfı"""
    
    # Türkçe karakterler
    TURKISH_LOWER = "abcçdefgğhıijklmnoöprsştuüvyz"
    TURKISH_UPPER = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
    
    # Türkçe karakter dönüşüm haritası
    TURKISH_CHAR_MAP = {
        'İ': 'i',
        'I': 'ı',
        'Ş': 'ş',
        'Ğ': 'ğ',
        'Ü': 'ü',
        'Ö': 'ö',
        'Ç': 'ç'
    }
    
    def __init__(self):
        """Text processor başlatıcı"""
        pass
    
    def turkish_lower(self, text: str) -> str:
        """
        Türkçe karakter kurallarına uygun küçük harf dönüşümü
        
        Args:
            text: Dönüştürülecek metin
            
        Returns:
            Küçük harfe dönüştürülmüş metin
        """
        result = ""
        for char in text:
            if char == 'İ':
                result += 'i'
            elif char == 'I':
                result += 'ı'
            else:
                result += char.lower()
        return result
    
    def turkish_upper(self, text: str) -> str:
        """
        Türkçe karakter kurallarına uygun büyük harf dönüşümü
        
        Args:
            text: Dönüştürülecek metin
            
        Returns:
            Büyük harfe dönüştürülmüş metin
        """
        result = ""
        for char in text:
            if char == 'i':
                result += 'İ'
            elif char == 'ı':
                result += 'I'
            else:
                result += char.upper()
        return result
    
    def clean_text(self, text: str, remove_punctuation: bool = False) -> str:
        """
        Metni temizler, gereksiz boşlukları kaldırır
        
        Args:
            text: Temizlenecek metin
            remove_punctuation: Noktalama işaretlerini kaldır (varsayılan: False)
            
        Returns:
            Temizlenmiş metin
        """
        if not text:
            return ""
        
        # Fazladan boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Noktalama işaretlerini kaldır (istenirse)
        if remove_punctuation:
            # Türkçe metinler için bazı noktalama işaretlerini koru
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def split_sentences(self, text: str) -> List[str]:
        """
        Türkçe noktalama kurallarına göre metni cümlelere ayırır
        
        Args:
            text: Cümlelere ayrılacak metin
            
        Returns:
            Cümle listesi
        """
        # Basit cümle ayırma (nokta, soru işareti, ünlem işareti)
        # Not: TurkishSplitter.java'daki mantığın basitleştirilmiş versiyonu
        
        # Kısaltmalar için koruma
        abbreviations = ['dr', 'prof', 'doç', 'yrd', 'bkz', 'vb', 'vs', 'örn']
        
        # Önce metni temizle
        text = self.clean_text(text)
        
        # Basit cümle ayırma regex'i
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Boş cümleleri kaldır
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def tokenize_words(self, text: str) -> List[str]:
        """
        Metni kelimelere ayırır
        
        Args:
            text: Tokenize edilecek metin
            
        Returns:
            Kelime listesi
        """
        # Kelime sınırlarına göre ayır
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Tek karakterleri ve sayıları filtrele
        words = [w for w in words if len(w) > 1 and not w.isdigit()]
        
        return words
    
    def extract_keywords(self, text: str, remove_stopwords: bool = True) -> List[str]:
        """
        Metinden anahtar kelimeleri çıkarır
        
        Args:
            text: Analiz edilecek metin
            remove_stopwords: Durak kelimelerini kaldır (varsayılan: True)
            
        Returns:
            Anahtar kelime listesi
        """
        # Önce küçük harfe çevir
        text = self.turkish_lower(text)
        
        # Kelimelere ayır
        words = self.tokenize_words(text)
        
        # Durak kelimeleri kaldır (istenirse)
        if remove_stopwords:
            stopwords = self._get_turkish_stopwords()
            words = [w for w in words if w not in stopwords]
        
        return words
    
    def _get_turkish_stopwords(self) -> set:
        """
        Türkçe durak kelimeleri döndürür
        
        Returns:
            Durak kelime seti
        """
        # Yaygın Türkçe durak kelimeler
        stopwords = {
            've', 'veya', 'ile', 'için', 'gibi', 'kadar', 'daha', 'çok', 
            'bir', 'bu', 'şu', 'o', 'mi', 'mı', 'mu', 'mü',
            'de', 'da', 'ki', 've', 'ama', 'fakat', 'ancak',
            'ya', 'ne', 'nasıl', 'neden', 'niçin', 'nerede', 'nereye',
            'var', 'yok', 'olan', 'olup', 'ise', 'bile',
            'ben', 'sen', 'o', 'biz', 'siz', 'onlar',
            'benim', 'senin', 'onun', 'bizim', 'sizin', 'onların',
            'her', 'hiç', 'bazı', 'birçok', 'tüm', 'bütün'
        }
        return stopwords
    
    def get_word_frequency(self, text: str) -> Dict[str, int]:
        """
        Metindeki kelime frekanslarını hesaplar
        
        Args:
            text: Analiz edilecek metin
            
        Returns:
            Kelime: Frekans sözlüğü
        """
        from collections import Counter
        
        words = self.extract_keywords(text, remove_stopwords=True)
        word_freq = Counter(words)
        
        return dict(word_freq)
    
    def normalize_text(self, text: str) -> str:
        """
        Metni normalize eder (küçük harf, temizlik, vb.)
        
        Args:
            text: Normalize edilecek metin
            
        Returns:
            Normalize edilmiş metin
        """
        # Küçük harfe çevir
        text = self.turkish_lower(text)
        
        # Temizle
        text = self.clean_text(text, remove_punctuation=False)
        
        return text


# Utility fonksiyonları
def process_text(text: str, clean: bool = True, lowercase: bool = True) -> str:
    """
    Hızlı metin işleme fonksiyonu
    
    Args:
        text: İşlenecek metin
        clean: Temizlik yap
        lowercase: Küçük harfe çevir
        
    Returns:
        İşlenmiş metin
    """
    processor = TurkishTextProcessor()
    
    if clean:
        text = processor.clean_text(text)
    
    if lowercase:
        text = processor.turkish_lower(text)
    
    return text


def split_to_sentences(text: str) -> List[str]:
    """
    Metni cümlelere ayıran yardımcı fonksiyon
    
    Args:
        text: Metin
        
    Returns:
        Cümle listesi
    """
    processor = TurkishTextProcessor()
    return processor.split_sentences(text)


def extract_words(text: str) -> List[str]:
    """
    Metinden kelimeleri çıkaran yardımcı fonksiyon
    
    Args:
        text: Metin
        
    Returns:
        Kelime listesi
    """
    processor = TurkishTextProcessor()
    return processor.tokenize_words(text)


# Test için
if __name__ == "__main__":
    processor = TurkishTextProcessor()
    
    # Test metni
    test_text = "Bu bir TEST metnİdİr. İstanbul'da deprem oldu! Çok korkutucu bİr durumdu."
    
    print("Orijinal metin:", test_text)
    print("\nKüçük harf:", processor.turkish_lower(test_text))
    print("\nBüyük harf:", processor.turkish_upper(test_text))
    print("\nCümleler:", processor.split_sentences(test_text))
    print("\nKelimeler:", processor.tokenize_words(test_text))
    print("\nAnahtar kelimeler:", processor.extract_keywords(test_text))
    print("\nKelime frekansları:", processor.get_word_frequency(test_text))

