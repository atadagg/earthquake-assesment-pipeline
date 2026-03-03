"""
Kategori Analizi v2 - İyileştirilmiş
Sadece AH ve ÇH kategorileri + Hasar tespitine özel kelime seçimi
"""

import pandas as pd
import re
from collections import Counter
from typing import Dict, List, Tuple
from text_processor import TurkishTextProcessor


class ImprovedCategoryAnalyzer:
    """İyileştirilmiş kategori analizi - Domain-specific stop words ile"""
    
    def __init__(self, excel_file: str):
        """
        Analiz ediciyi başlat
        
        Args:
            excel_file: Excel dosyası yolu
        """
        self.excel_file = excel_file
        self.df = None
        self.processor = TurkishTextProcessor()
        self.category_keywords = {}
        self.train_data = None
        self.test_data = None
        
        # Hasar tespitine özel durak kelimeler
        self.domain_stopwords = self._get_domain_stopwords()
    
    def _get_domain_stopwords(self) -> set:
        """
        Hasar tespiti için özel durak kelimeler
        Adres, lokasyon, genel kelimeler - hasar belirtmeyen kelimeler
        
        Returns:
            Domain-specific stop words
        """
        return {
            # Adres kelimeleri
            'mahallesi', 'mahalle', 'apartmanı', 'apartman', 'sitesi', 'site',
            'caddesi', 'cadde', 'sokak', 'sokağı', 'bulvarı', 'bulvar',
            'no', 'numara', 'kat', 'daire',
            
            # Şehir/bölge isimleri
            'hatay', 'antakya', 'kahramanmaraş', 'adıyaman', 'malatya',
            'gaziantep', 'osmaniye', 'diyarbakır', 'şanlıurfa',
            'elbistan', 'pazarcık', 'nurdağı', 'islahiye',
            
            # Genel kelimeler
            'lütfen', 'rica', 'rica ederim', 'teşekkür', 'teşekkürler',
            'acilen', 'hemen', 'ivedilikle',
            
            # Kişi/iletişim
            'isim', 'ad', 'soyad', 'telefon', 'numara', 'arayın', 'arayin',
            
            # Link/referans
            'http', 'https', 'twitter', 'com', 'facebook', 'instagram',
            
            # Zaman
            'saat', 'dakika', 'gün', 'sabah', 'öğle', 'akşam', 'gece',
            
            # Sayılar/numaralar (regex ile de yakalanır ama ekstra)
            'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz', 'on'
        }
    
    def load_data(self):
        """Excel dosyasını yükle - Sadece AH ve ÇH"""
        print(f"📂 Veri yükleniyor: {self.excel_file}")
        df = pd.read_excel(self.excel_file)
        
        # Sadece AH ve ÇH kategorilerini al
        self.df = df[df['AOD'].isin(['AH', 'ÇH'])].copy()
        
        print(f"✓ Yüklendi: {len(self.df)} kayıt (sadece AH ve ÇH)")
        print(f"  - ÇH: {len(self.df[self.df['AOD'] == 'ÇH'])} kayıt")
        print(f"  - AH: {len(self.df[self.df['AOD'] == 'AH'])} kayıt")
        
        # TEXT sütunundaki NaN değerleri boş string yap
        if 'TEXT' in self.df.columns:
            self.df['TEXT'] = self.df['TEXT'].fillna('')
        
        return self.df
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Metinden hasar tespitine uygun kelimeleri çıkar
        Domain-specific stop words filtrele
        
        Args:
            text: Metin
            
        Returns:
            Kelime listesi
        """
        # Önce normal keyword extraction
        keywords = self.processor.extract_keywords(text, remove_stopwords=True)
        
        # Domain-specific stop words'leri çıkar
        keywords = [kw for kw in keywords if kw not in self.domain_stopwords]
        
        # Çok kısa kelimeleri çıkar (< 3 karakter)
        keywords = [kw for kw in keywords if len(kw) >= 3]
        
        return keywords
    
    def extract_top_keywords_per_category(self, top_n: int = 10) -> Dict[str, List[str]]:
        """
        Her kategori için en çok geçen AYIRT EDİCİ kelimeleri bul
        
        Args:
            top_n: Her kategori için kaç kelime (varsayılan: 10)
            
        Returns:
            {kategori: [kelime1, kelime2, ...]} sözlüğü
        """
        if self.df is None:
            self.load_data()
        
        categories = ['ÇH', 'AH']
        
        print(f"\n🔍 İYİLEŞTİRİLMİŞ KELİME ANALİZİ")
        print(f"{'='*60}")
        print("Domain-specific stop words filtreleniyor:")
        print(f"  Filtrelenen kelime sayısı: {len(self.domain_stopwords)}")
        print(f"  Örnek: {', '.join(list(self.domain_stopwords)[:10])}...")
        
        self.category_keywords = {}
        
        for category in categories:
            print(f"\n{'='*60}")
            print(f"📊 Kategori: {category}")
            print(f"{'='*60}")
            
            # Bu kategorideki tüm metinleri al
            category_texts = self.df[self.df['AOD'] == category]['TEXT'].tolist()
            print(f"Toplam metin: {len(category_texts)}")
            
            # Tüm kelimeleri topla (iyileştirilmiş extraction ile)
            all_words = []
            for text in category_texts:
                if isinstance(text, str) and text.strip():
                    words = self.extract_keywords(text)
                    all_words.extend(words)
            
            # En çok geçen kelimeleri bul
            word_counts = Counter(all_words)
            top_keywords = [word for word, count in word_counts.most_common(top_n)]
            
            self.category_keywords[category] = top_keywords
            
            print(f"\n✓ En çok geçen {top_n} AYIRT EDİCİ kelime:")
            for i, (word, count) in enumerate(word_counts.most_common(top_n), 1):
                print(f"  {i:2d}. {word:20s} ({count:4d} kez)")
        
        # Çakışan kelimeleri göster
        print(f"\n{'='*60}")
        print("🔍 KELİME ÇAKIŞMA ANALİZİ")
        print(f"{'='*60}")
        
        ch_keywords = set(self.category_keywords['ÇH'])
        ah_keywords = set(self.category_keywords['AH'])
        
        overlap = ch_keywords & ah_keywords
        ch_unique = ch_keywords - ah_keywords
        ah_unique = ah_keywords - ch_keywords
        
        print(f"\nÇH'ye ÖZGÜ kelimeler ({len(ch_unique)}):")
        print(f"  {', '.join(ch_unique)}")
        
        print(f"\nAH'ye ÖZGÜ kelimeler ({len(ah_unique)}):")
        print(f"  {', '.join(ah_unique)}")
        
        print(f"\nORTAK kelimeler ({len(overlap)}):")
        if overlap:
            print(f"  {', '.join(overlap)}")
        else:
            print(f"  ✓ Hiç ortak kelime yok! Mükemmel ayırım.")
        
        return self.category_keywords
    
    def classify_text(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Metni kategorilere göre sınıflandır
        
        Args:
            text: Sınıflandırılacak metin
            
        Returns:
            (tahmin_edilen_kategori, {kategori: eşleşme_sayısı})
        """
        if not self.category_keywords:
            raise ValueError("Önce extract_top_keywords_per_category() çalıştırılmalı!")
        
        # Metni işle (iyileştirilmiş extraction ile)
        text_words = set(self.extract_keywords(text))
        
        # Her kategori için eşleşme sayısını hesapla
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_words)
            category_scores[category] = matches
        
        # En yüksek skora sahip kategoriyi döndür
        if category_scores:
            # Eğer skorlar eşitse, majority class'ı döndür (ÇH)
            max_score = max(category_scores.values())
            if max_score == 0:
                # Hiç eşleşme yoksa ÇH döndür (majority class)
                return 'ÇH', category_scores
            
            predicted_category = max(category_scores, key=category_scores.get)
            return predicted_category, category_scores
        
        return 'ÇH', category_scores  # Default: majority class
    
    def split_train_test(self, test_ratio: float = 0.2, random_state: int = 42):
        """
        Veriyi train ve test olarak ayır - Stratified
        
        Args:
            test_ratio: Test veri oranı (varsayılan: 0.2)
            random_state: Random seed
        """
        if self.df is None:
            self.load_data()
        
        # Stratified split için her kategoriden ayrı ayır
        train_list = []
        test_list = []
        
        for category in ['AH', 'ÇH']:
            cat_data = self.df[self.df['AOD'] == category]
            cat_shuffled = cat_data.sample(frac=1, random_state=random_state).reset_index(drop=True)
            
            split_index = int(len(cat_shuffled) * (1 - test_ratio))
            train_list.append(cat_shuffled[:split_index])
            test_list.append(cat_shuffled[split_index:])
        
        self.train_data = pd.concat(train_list, ignore_index=True)
        self.test_data = pd.concat(test_list, ignore_index=True)
        
        print(f"\n📊 STRATIFIED VERİ BÖLME:")
        print(f"{'='*60}")
        print(f"Train: {len(self.train_data)} kayıt ({(1-test_ratio)*100:.0f}%)")
        print(f"  - ÇH: {len(self.train_data[self.train_data['AOD'] == 'ÇH'])}")
        print(f"  - AH: {len(self.train_data[self.train_data['AOD'] == 'AH'])}")
        
        print(f"\nTest:  {len(self.test_data)} kayıt ({test_ratio*100:.0f}%)")
        print(f"  - ÇH: {len(self.test_data[self.test_data['AOD'] == 'ÇH'])}")
        print(f"  - AH: {len(self.test_data[self.test_data['AOD'] == 'AH'])}")
        
        return self.train_data, self.test_data
    
    def train(self, top_n: int = 10):
        """
        Train verisi ile modeli eğit
        
        Args:
            top_n: Her kategori için kaç kelime
        """
        if self.train_data is None:
            self.split_train_test()
        
        print(f"\n🎓 EĞİTİM BAŞLIYOR (İyileştirilmiş)...")
        print(f"{'='*60}")
        
        # Geçici olarak self.df'i train_data yap
        original_df = self.df
        self.df = self.train_data
        
        # Top keywords çıkar
        self.extract_top_keywords_per_category(top_n=top_n)
        
        # self.df'i geri yükle
        self.df = original_df
        
        print(f"\n✓ Eğitim tamamlandı!")
    
    def test(self) -> Dict:
        """Test verisi ile modeli test et"""
        if self.test_data is None:
            raise ValueError("Önce split_train_test() çalıştırılmalı!")
        
        if not self.category_keywords:
            raise ValueError("Önce train() çalıştırılmalı!")
        
        print(f"\n🧪 TEST BAŞLIYOR...")
        print(f"{'='*60}")
        print(f"Test verisi: {len(self.test_data)} kayıt\n")
        
        correct = 0
        total = 0
        predictions = []
        
        # Kategori bazlı istatistikler
        category_stats = {
            'ÇH': {'correct': 0, 'total': 0, 'predicted_as_ch': 0, 'predicted_as_ah': 0},
            'AH': {'correct': 0, 'total': 0, 'predicted_as_ch': 0, 'predicted_as_ah': 0}
        }
        
        for idx, row in self.test_data.iterrows():
            text = row['TEXT']
            true_category = row['AOD']
            
            if not isinstance(text, str) or not text.strip():
                continue
            
            predicted_category, scores = self.classify_text(text)
            
            predictions.append({
                'ID': row['ID'],
                'text': text[:100],
                'true': true_category,
                'predicted': predicted_category,
                'ch_score': scores.get('ÇH', 0),
                'ah_score': scores.get('AH', 0)
            })
            
            total += 1
            if predicted_category == true_category:
                correct += 1
                category_stats[true_category]['correct'] += 1
            
            category_stats[true_category]['total'] += 1
            
            # Confusion matrix için
            if predicted_category == 'ÇH':
                category_stats[true_category]['predicted_as_ch'] += 1
            else:
                category_stats[true_category]['predicted_as_ah'] += 1
        
        # Genel başarı oranı
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Precision ve Recall hesapla
        # ÇH için
        ch_tp = category_stats['ÇH']['correct']
        ch_total_predicted = category_stats['ÇH']['predicted_as_ch'] + category_stats['AH']['predicted_as_ch']
        ch_precision = (ch_tp / ch_total_predicted * 100) if ch_total_predicted > 0 else 0
        ch_recall = (ch_tp / category_stats['ÇH']['total'] * 100) if category_stats['ÇH']['total'] > 0 else 0
        ch_f1 = (2 * ch_precision * ch_recall / (ch_precision + ch_recall)) if (ch_precision + ch_recall) > 0 else 0
        
        # AH için
        ah_tp = category_stats['AH']['correct']
        ah_total_predicted = category_stats['AH']['predicted_as_ah'] + category_stats['ÇH']['predicted_as_ah']
        ah_precision = (ah_tp / ah_total_predicted * 100) if ah_total_predicted > 0 else 0
        ah_recall = (ah_tp / category_stats['AH']['total'] * 100) if category_stats['AH']['total'] > 0 else 0
        ah_f1 = (2 * ah_precision * ah_recall / (ah_precision + ah_recall)) if (ah_precision + ah_recall) > 0 else 0
        
        # Sonuçlar
        results = {
            'total': total,
            'correct': correct,
            'incorrect': total - correct,
            'accuracy': accuracy,
            'category_stats': category_stats,
            'ch_precision': ch_precision,
            'ch_recall': ch_recall,
            'ch_f1': ch_f1,
            'ah_precision': ah_precision,
            'ah_recall': ah_recall,
            'ah_f1': ah_f1,
            'predictions': predictions
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Test sonuçlarını yazdır"""
        print("\n" + "="*60)
        print("📈 TEST SONUÇLARI (İyileştirilmiş)")
        print("="*60)
        
        print(f"\nGenel Performans:")
        print(f"  Toplam Test: {results['total']}")
        print(f"  Doğru: {results['correct']} ✓")
        print(f"  Yanlış: {results['incorrect']} ✗")
        print(f"  Başarı Oranı: {results['accuracy']:.2f}%")
        
        print(f"\nDetaylı Metrikler:")
        print(f"\n  ÇH (Çok Hasarlı):")
        stats = results['category_stats']['ÇH']
        print(f"    Accuracy:  {stats['correct']}/{stats['total']} ({stats['correct']/stats['total']*100:.1f}%)")
        print(f"    Precision: {results['ch_precision']:.1f}%")
        print(f"    Recall:    {results['ch_recall']:.1f}%")
        print(f"    F1-Score:  {results['ch_f1']:.1f}%")
        
        print(f"\n  AH (Az Hasarlı):")
        stats = results['category_stats']['AH']
        print(f"    Accuracy:  {stats['correct']}/{stats['total']} ({stats['correct']/stats['total']*100:.1f}%)")
        print(f"    Precision: {results['ah_precision']:.1f}%")
        print(f"    Recall:    {results['ah_recall']:.1f}%")
        print(f"    F1-Score:  {results['ah_f1']:.1f}%")
        
        print("\n" + "="*60)
    
    def save_results(self, results: Dict, output_file: str = 'improved_results.csv'):
        """Sonuçları kaydet"""
        predictions_df = pd.DataFrame(results['predictions'])
        predictions_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 Sonuçlar kaydedildi: {output_file}")


def main():
    """Ana fonksiyon"""
    print("\n" + "="*60)
    print("İYİLEŞTİRİLMİŞ KATEGORİ ANALİZİ")
    print("Sadece AH ve ÇH + Domain-Specific Stop Words")
    print("="*60)
    
    # Analyzer oluştur
    analyzer = ImprovedCategoryAnalyzer('Deprem_Hasarlı_Data.xlsx')
    
    # Veriyi yükle (sadece AH ve ÇH)
    analyzer.load_data()
    
    # Train/Test ayır (stratified)
    analyzer.split_train_test(test_ratio=0.2)
    
    # Eğit (iyileştirilmiş kelime seçimi)
    analyzer.train(top_n=10)
    
    # Test et
    results = analyzer.test()
    
    # Sonuçları göster
    analyzer.print_results(results)
    
    # Kaydet
    analyzer.save_results(results)
    
    print("\n✅ İşlem tamamlandı!")


if __name__ == "__main__":
    main()

