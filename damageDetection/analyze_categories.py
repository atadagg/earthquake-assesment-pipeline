"""
Kategori Analizi ve Sınıflandırma
Her kategori (AH, OH, ÇH) için en çok geçen kelimeleri bulur ve yeni verileri sınıflandırır.
"""

import pandas as pd
from collections import Counter
from typing import Dict, List, Tuple, Optional, Any
from text_processor import TurkishTextProcessor


class CategoryAnalyzer:
    """Kategori bazlı kelime analizi ve sınıflandırma"""
    
    def __init__(self, excel_file: str):
        """
        Analiz ediciyi başlat
        
        Args:
            excel_file: Excel dosyası yolu
        """
        self.excel_file = excel_file
        self.df: Optional[pd.DataFrame] = None
        self.processor = TurkishTextProcessor()
        self.category_keywords: Dict[str, List[str]] = {}  # Her kategori için top 10 kelime
        self.train_data: Optional[pd.DataFrame] = None
        self.test_data: Optional[pd.DataFrame] = None
        
    def load_data(self):
        """Excel dosyasını yükle"""
        print(f"📂 Veri yükleniyor: {self.excel_file}")
        self.df = pd.read_excel(self.excel_file)
        print(f"✓ Yüklendi: {len(self.df)} kayıt")
        
        # TEXT sütunundaki NaN değerleri boş string yap
        if 'TEXT' in self.df.columns:
            self.df['TEXT'] = self.df['TEXT'].fillna('')
        
        return self.df
    
    def extract_top_keywords_per_category(self, categories: Optional[List[str]] = None, top_n: int = 10) -> Dict[str, List[str]]:
        """
        Her kategori için en çok geçen kelimeleri bul
        
        Args:
            categories: Analiz edilecek kategoriler (None ise hepsi)
            top_n: Her kategori için kaç kelime (varsayılan: 10)
            
        Returns:
            {kategori: [kelime1, kelime2, ...]} sözlüğü
        """
        if self.df is None:
            self.load_data()
            
        assert self.df is not None, "DataFrame verisi yüklenemedi."
        
        if categories is None:
            # En çok olan 3 kategoriyi al
            categories = self.df['AOD'].value_counts().head(3).index.tolist()
        
        print("\n🔍 Kategori analizi başlıyor...")
        print(f"Kategoriler: {', '.join(categories)}")
        
        self.category_keywords = {}
        
        for category in categories:
            print(f"\n{'='*60}")
            print(f"📊 Kategori: {category}")
            print(f"{'='*60}")
            
            # Bu kategorideki tüm metinleri al
            category_texts = self.df[self.df['AOD'] == category]['TEXT'].tolist()
            print(f"Toplam metin: {len(category_texts)}")
            
            # Tüm kelimeleri topla
            all_words = []
            for text in category_texts:
                if isinstance(text, str) and text.strip():
                    # Metni temizle ve kelimelere ayır
                    words = self.processor.extract_keywords(text, remove_stopwords=True)
                    all_words.extend(words)
            
            # En çok geçen kelimeleri bul
            word_counts = Counter(all_words)
            top_keywords = [word for word, count in word_counts.most_common(top_n)]
            
            self.category_keywords[category] = top_keywords
            
            print(f"\n✓ En çok geçen {top_n} kelime:")
            for i, (word, count) in enumerate(word_counts.most_common(top_n), 1):
                print(f"  {i:2d}. {word:20s} ({count:4d} kez)")
        
        return self.category_keywords
    
    def classify_text(self, text: str) -> Tuple[Optional[str], Dict[str, int]]:
        """
        Metni kategorilere göre sınıflandır
        
        Args:
            text: Sınıflandırılacak metin
            
        Returns:
            (tahmin_edilen_kategori, {kategori: eşleşme_sayısı})
        """
        if not self.category_keywords:
            raise ValueError("Önce extract_top_keywords_per_category() çalıştırılmalı!")
        
        # Metni işle
        text_lower = self.processor.turkish_lower(text)
        text_words = set(self.processor.extract_keywords(text_lower, remove_stopwords=True))
        
        # Her kategori için eşleşme sayısını hesapla
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            # Bu kategorinin kaç kelimesi metinde geçiyor
            matches = sum(1 for keyword in keywords if keyword in text_words)
            category_scores[category] = matches
        
        # En yüksek skora sahip kategoriyi döndür
        if category_scores:
            predicted_category = max(category_scores, key=category_scores.get)
            return predicted_category, category_scores
        
        return None, category_scores
    
    def split_train_test(self, test_ratio: float = 0.2, random_state: int = 42):
        """
        Veriyi train ve test olarak ayır
        
        Args:
            test_ratio: Test veri oranı (varsayılan: 0.2 = %20)
            random_state: Random seed
        """
        if self.df is None:
            self.load_data()
        
        # Sadece en çok olan 3 kategoriyi al
        top_categories = self.df['AOD'].value_counts().head(3).index.tolist()
        df_filtered = self.df[self.df['AOD'].isin(top_categories)].copy()
        
        # Karıştır ve ayır
        df_shuffled = df_filtered.sample(frac=1, random_state=random_state).reset_index(drop=True)
        
        split_index = int(len(df_shuffled) * (1 - test_ratio))
        self.train_data = df_shuffled[:split_index]
        self.test_data = df_shuffled[split_index:]
        
        print("\n📊 Veri Bölme:")
        print(f"  Train: {len(self.train_data)} kayıt ({(1-test_ratio)*100:.0f}%)")
        print(f"  Test:  {len(self.test_data)} kayıt ({test_ratio*100:.0f}%)")
        
        return self.train_data, self.test_data
    
    def train(self, top_n: int = 10):
        """
        Train verisi ile modeli eğit (top keywords çıkar)
        
        Args:
            top_n: Her kategori için kaç kelime
        """
        if self.train_data is None:
            self.split_train_test()
        
        print("\n🎓 EĞİTİM BAŞLIYOR...")
        
        # Train verisinden top keywords çıkar
        categories = self.train_data['AOD'].value_counts().index.tolist()
        
        self.category_keywords = {}
        for category in categories:
            category_texts = self.train_data[self.train_data['AOD'] == category]['TEXT'].tolist()
            
            all_words = []
            for text in category_texts:
                if isinstance(text, str) and text.strip():
                    words = self.processor.extract_keywords(text, remove_stopwords=True)
                    all_words.extend(words)
            
            word_counts = Counter(all_words)
            top_keywords = [word for word, count in word_counts.most_common(top_n)]
            self.category_keywords[category] = top_keywords
            
            print(f"\n✓ {category} kategorisi: {len(category_texts)} metin, {top_n} anahtar kelime")
            print(f"  Kelimeler: {', '.join(top_keywords[:5])}...")
        
        print("\n✓ Eğitim tamamlandı!")
    
    def test(self) -> Dict[str, Any]:
        """
        Test verisi ile modeli test et ve başarı oranını hesapla
        
        Returns:
            Sonuç metrikleri
        """
        if self.test_data is None:
            raise ValueError("Önce split_train_test() veya train() çalıştırılmalı!")
        
        if not self.category_keywords:
            raise ValueError("Önce train() çalıştırılmalı!")
        
        print("\n🧪 TEST BAŞLIYOR...")
        print(f"Test verisi: {len(self.test_data)} kayıt\n")
        
        correct: int = 0
        total: int = 0
        predictions: List[Dict[str, Any]] = []
        
        # Kategori bazlı istatistikler
        category_stats: Dict[str, Dict[str, int]] = {cat: {'correct': 0, 'total': 0} for cat in self.category_keywords.keys()}
        
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
                'scores': scores
            })
            
            total += 1
            if predicted_category == true_category:
                correct += 1
                category_stats[true_category]['correct'] += 1
            
            category_stats[true_category]['total'] += 1
        
        # Genel başarı oranı
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Sonuçlar
        results = {
            'total': total,
            'correct': correct,
            'incorrect': total - correct,
            'accuracy': accuracy,
            'category_stats': category_stats,
            'predictions': predictions
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Test sonuçlarını yazdır"""
        print("\n" + "="*60)
        print("📈 TEST SONUÇLARI")
        print("="*60)
        
        print("\nGenel Performans:")
        print(f"  Toplam Test: {results['total']}")
        print(f"  Doğru: {results['correct']} ✓")
        print(f"  Yanlış: {results['incorrect']} ✗")
        print(f"  Başarı Oranı: {results['accuracy']:.2f}%")
        
        print("\nKategori Bazlı Performans:")
        for category, stats in results['category_stats'].items():
            if stats['total'] > 0:
                cat_accuracy = (stats['correct'] / stats['total'] * 100)
                print(f"  {category}: {stats['correct']}/{stats['total']} ({cat_accuracy:.1f}%)")
        
        print("\n" + "="*60)
    
    def save_results(self, results: Dict[str, Any], output_file: str = 'classification_results.csv'):
        """Sonuçları CSV'ye kaydet"""
        predictions_df = pd.DataFrame(results['predictions'])
        predictions_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 Sonuçlar kaydedildi: {output_file}")


def main():
    """Ana fonksiyon"""
    print("\n" + "="*60)
    print("KATEGORİ ANALİZİ VE SINIFLANDIRMA")
    print("="*60)
    
    # Analyzer oluştur
    analyzer = CategoryAnalyzer('Deprem_Hasarlı_Data.xlsx')
    
    # Veriyi yükle
    analyzer.load_data()
    
    # Train/Test ayır
    analyzer.split_train_test(test_ratio=0.2)
    
    # Eğit (her kategori için top 10 kelime bul)
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

