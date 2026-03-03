"""
Ana Kategorizasyon Scripti
Excel dosyasından AOD='ÇH' olan kayıtları okur ve 10 anahtar kelimeye göre kategorize eder.
"""

import pandas as pd
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Modülleri import et
from text_processor import TurkishTextProcessor
from keyword_matcher import KeywordMatcher, KeywordLoader


class EarthquakeDataCategorizer:
    """Deprem verilerini kategorize eden ana sınıf"""
    
    def __init__(self, keywords: List[str]):
        """
        Kategorize edici başlatıcı
        
        Args:
            keywords: 10 anahtar kelime listesi
        """
        self.keywords = keywords
        self.text_processor = TurkishTextProcessor()
        self.keyword_matcher = KeywordMatcher(keywords)
        self.data = None
        self.filtered_data = None
        self.results = None
    
    def load_excel(self, file_path: str) -> pd.DataFrame:
        """
        Excel dosyasını yükler
        
        Args:
            file_path: Excel dosyası yolu
            
        Returns:
            DataFrame
        """
        try:
            print(f"Excel dosyası yükleniyor: {file_path}")
            self.data = pd.read_excel(file_path)
            print(f"✓ Başarıyla yüklendi. Toplam kayıt: {len(self.data)}")
            print(f"✓ Sütunlar: {list(self.data.columns)}")
            return self.data
        except FileNotFoundError:
            print(f"✗ HATA: {file_path} dosyası bulunamadı!")
            sys.exit(1)
        except Exception as e:
            print(f"✗ HATA: Excel dosyası yüklenirken hata oluştu: {e}")
            sys.exit(1)
    
    def filter_by_aod(self, aod_value: str = "ÇH") -> pd.DataFrame:
        """
        AOD sütununa göre verileri filtreler
        
        Args:
            aod_value: Filtrelenecek AOD değeri (varsayılan: "ÇH")
            
        Returns:
            Filtrelenmiş DataFrame
        """
        if self.data is None:
            print("✗ HATA: Önce Excel dosyasını yüklemelisiniz!")
            return None
        
        if 'AOD' not in self.data.columns:
            print("✗ HATA: Excel dosyasında 'AOD' sütunu bulunamadı!")
            print(f"Mevcut sütunlar: {list(self.data.columns)}")
            return None
        
        print(f"\nAOD='{aod_value}' filtresi uygulanıyor...")
        self.filtered_data = self.data[self.data['AOD'] == aod_value].copy()
        print(f"✓ Filtrelendi. AOD='{aod_value}' kayıt sayısı: {len(self.filtered_data)}")
        
        return self.filtered_data
    
    def categorize_texts(self) -> List[Dict]:
        """
        Filtrelenmiş metinleri kategorize eder
        
        Returns:
            Kategorizasyon sonuçları listesi
        """
        if self.filtered_data is None or len(self.filtered_data) == 0:
            print("✗ HATA: Kategorize edilecek veri yok!")
            return []
        
        if 'text' not in self.filtered_data.columns:
            print("✗ HATA: Excel dosyasında 'text' sütunu bulunamadı!")
            return []
        
        print(f"\n{len(self.filtered_data)} metin kategorize ediliyor...")
        
        results = []
        for idx, row in self.filtered_data.iterrows():
            text = str(row['text'])
            
            # Kategorizasyon
            categorization = self.keyword_matcher.categorize_text(text)
            
            # Orijinal veriyi ekle
            result = {
                'ID': row.get('ID', idx),
                'filename': row.get('filename', ''),
                'text': text,
                'label': row.get('label', ''),
                'AOD': row.get('AOD', ''),
                'matched_keywords': categorization['matched_keywords'],
                'keyword_count': categorization['keyword_count'],
                'total_matches': categorization['total_matches'],
            }
            
            # Her anahtar kelime için ayrı sütun
            for keyword in self.keywords:
                result[f'kategori_{keyword}'] = categorization['keyword_presence'][keyword]
                result[f'frekans_{keyword}'] = categorization['keyword_frequencies'][keyword]
            
            results.append(result)
        
        self.results = results
        print(f"✓ Kategorizasyon tamamlandı!")
        
        return results
    
    def save_results_to_csv(self, output_path: str):
        """
        Sonuçları CSV dosyasına kaydeder
        
        Args:
            output_path: Çıktı dosyası yolu
        """
        if not self.results:
            print("✗ HATA: Kaydedilecek sonuç yok!")
            return
        
        print(f"\nSonuçlar CSV'ye kaydediliyor: {output_path}")
        df_results = pd.DataFrame(self.results)
        df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✓ Başarıyla kaydedildi: {output_path}")
    
    def save_statistics_to_json(self, output_path: str):
        """
        İstatistikleri JSON dosyasına kaydeder
        
        Args:
            output_path: Çıktı dosyası yolu
        """
        if not self.results:
            print("✗ HATA: İstatistik hesaplanamıyor!")
            return
        
        # İstatistikleri hesapla
        texts = [r['text'] for r in self.results]
        stats = self.keyword_matcher.get_statistics(texts)
        
        # Ek bilgiler ekle
        stats['analysis_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats['keywords'] = self.keywords
        stats['aod_filter'] = "ÇH"
        
        print(f"\nİstatistikler JSON'a kaydediliyor: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"✓ Başarıyla kaydedildi: {output_path}")
    
    def print_summary(self):
        """Özet istatistikleri ekrana yazdırır"""
        if not self.results:
            print("✗ HATA: Özet gösterilemez!")
            return
        
        texts = [r['text'] for r in self.results]
        stats = self.keyword_matcher.get_statistics(texts)
        
        print("\n" + "="*60)
        print("KATEGORİZASYON ÖZETİ")
        print("="*60)
        print(f"Toplam Analiz Edilen Metin: {stats['total_texts']}")
        print(f"Anahtar Kelime İçeren Metin: {stats['texts_with_matches']}")
        print(f"Anahtar Kelime İçermeyen Metin: {stats['texts_without_matches']}")
        print(f"Eşleşme Oranı: {stats['match_rate']:.2f}%")
        print(f"Ortalama Anahtar Kelime/Metin: {stats['avg_keywords_per_text']:.2f}")
        
        print("\nANAHTAR KELİME DAĞILIMI:")
        print("-" * 60)
        for keyword in self.keywords:
            count = stats['keyword_distribution'].get(keyword, 0)
            percentage = stats['keyword_percentages'].get(keyword, 0)
            print(f"  {keyword:20s}: {count:5d} metin ({percentage:5.2f}%)")
        
        print("="*60)
    
    def run(self, excel_path: str, aod_filter: str, output_csv: str, output_json: str):
        """
        Tüm işlem akışını çalıştırır
        
        Args:
            excel_path: Girdi Excel dosyası
            aod_filter: AOD filtre değeri
            output_csv: Çıktı CSV dosyası
            output_json: Çıktı JSON dosyası
        """
        print("\n" + "="*60)
        print("DEPREM VERİLERİ KATEGORİZASYON SİSTEMİ")
        print("="*60)
        
        # 1. Excel'i yükle
        self.load_excel(excel_path)
        
        # 2. AOD filtresini uygula
        self.filter_by_aod(aod_filter)
        
        # 3. Kategorize et
        self.categorize_texts()
        
        # 4. Sonuçları kaydet
        self.save_results_to_csv(output_csv)
        self.save_statistics_to_json(output_json)
        
        # 5. Özeti göster
        self.print_summary()
        
        print("\n✓ Tüm işlemler başarıyla tamamlandı!")


def main():
    """Ana fonksiyon - Komut satırı argümanlarını işler"""
    parser = argparse.ArgumentParser(
        description='Deprem verilerini 10 anahtar kelimeye göre kategorize eder'
    )
    
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Girdi Excel dosyası (.xlsx)'
    )
    
    parser.add_argument(
        '--keywords',
        type=str,
        default='keywords.txt',
        help='Anahtar kelime dosyası (varsayılan: keywords.txt)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='categorized_results.csv',
        help='Çıktı CSV dosyası (varsayılan: categorized_results.csv)'
    )
    
    parser.add_argument(
        '--stats',
        type=str,
        default='statistics.json',
        help='İstatistik JSON dosyası (varsayılan: statistics.json)'
    )
    
    parser.add_argument(
        '--aod-filter',
        type=str,
        default='ÇH',
        help='AOD filtre değeri (varsayılan: ÇH)'
    )
    
    args = parser.parse_args()
    
    # Anahtar kelimeleri yükle
    keywords = KeywordLoader.load_from_file(args.keywords)
    
    if len(keywords) == 0:
        print(f"✗ HATA: {args.keywords} dosyasından anahtar kelime yüklenemedi!")
        sys.exit(1)
    
    if len(keywords) != 10:
        print(f"⚠ UYARI: {len(keywords)} anahtar kelime bulundu. 10 kelime bekleniyor.")
    
    print(f"\nYüklenen anahtar kelimeler: {', '.join(keywords)}")
    
    # Kategorize ediciyi oluştur ve çalıştır
    categorizer = EarthquakeDataCategorizer(keywords)
    categorizer.run(
        excel_path=args.input,
        aod_filter=args.aod_filter,
        output_csv=args.output,
        output_json=args.stats
    )


if __name__ == "__main__":
    main()

