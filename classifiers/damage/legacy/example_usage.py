"""
Örnek Kullanım Scripti
Kategorizasyon sisteminin nasıl kullanılacağını gösterir.
"""

from text_processor import TurkishTextProcessor
from keyword_matcher import KeywordMatcher, KeywordLoader
from categorize_earthquake_data import EarthquakeDataCategorizer


def example_1_text_processing():
    """Örnek 1: Temel metin işleme"""
    print("\n" + "="*60)
    print("ÖRNEK 1: TEKSTİL İŞLEME")
    print("="*60)
    
    processor = TurkishTextProcessor()
    
    # Test metni
    text = "İSTANBUL'da büyük deprem oldu! Çok sayıda bina yıkıldı."
    
    print(f"\nOrijinal metin: {text}")
    print(f"Küçük harf: {processor.turkish_lower(text)}")
    print(f"Büyük harf: {processor.turkish_upper(text)}")
    print(f"Temizlenmiş: {processor.clean_text(text)}")
    print(f"Cümleler: {processor.split_sentences(text)}")
    print(f"Kelimeler: {processor.tokenize_words(text)}")
    print(f"Anahtar kelimeler: {processor.extract_keywords(text)}")


def example_2_keyword_matching():
    """Örnek 2: Anahtar kelime eşleştirme"""
    print("\n" + "="*60)
    print("ÖRNEK 2: ANAHTAR KELİME EŞLEŞTİRME")
    print("="*60)
    
    # Anahtar kelimeler
    keywords = [
        "deprem", "afet", "yardım", "enkaz", "kurtarma",
        "yıkım", "kayıp", "hastane", "barınak", "koordinasyon"
    ]
    
    matcher = KeywordMatcher(keywords)
    
    # Test metni
    text = """
    6 Şubat sabahı meydana gelen deprem büyük yıkıma neden oldu.
    Enkaz altında kalan yüzlerce kişi için kurtarma çalışmaları başlatıldı.
    Yardım ekipleri bölgeye ulaştı ve hastanelerde tedaviler sürüyor.
    """
    
    print(f"\nTest Metni:\n{text}")
    
    # Kategorizasyon
    result = matcher.categorize_text(text)
    
    print(f"\nEşleşen Anahtar Kelimeler: {result['matched_keywords']}")
    print(f"Toplam Anahtar Kelime: {result['keyword_count']}")
    print(f"Toplam Eşleşme: {result['total_matches']}")
    
    print("\nKelime Frekansları:")
    for keyword, count in result['keyword_frequencies'].items():
        if count > 0:
            print(f"  - {keyword}: {count}")


def example_3_multiple_texts():
    """Örnek 3: Çoklu metin analizi"""
    print("\n" + "="*60)
    print("ÖRNEK 3: ÇOKLU METİN ANALİZİ")
    print("="*60)
    
    # Anahtar kelimeler
    keywords = [
        "deprem", "afet", "yardım", "enkaz", "kurtarma",
        "yıkım", "kayıp", "hastane", "barınak", "koordinasyon"
    ]
    
    matcher = KeywordMatcher(keywords)
    
    # Test metinleri
    texts = [
        "Deprem bölgesinde enkaz kaldırma çalışmaları devam ediyor.",
        "Yardım kampanyaları organize ediliyor ve barınaklar kuruluyor.",
        "Kurtarma ekipleri koordinasyon içinde çalışıyor.",
        "Hastanelerde yaralıların tedavisi sürüyor.",
        "Bu metin depremle ilgili anahtar kelime içermiyor."
    ]
    
    print(f"\nToplam {len(texts)} metin analiz ediliyor...\n")
    
    # İstatistikleri al
    stats = matcher.get_statistics(texts)
    
    print(f"Toplam Metin: {stats['total_texts']}")
    print(f"Eşleşme İçeren: {stats['texts_with_matches']}")
    print(f"Eşleşme İçermeyen: {stats['texts_without_matches']}")
    print(f"Eşleşme Oranı: {stats['match_rate']:.2f}%")
    print(f"Ortalama Kelime/Metin: {stats['avg_keywords_per_text']:.2f}")
    
    print("\nAnahtar Kelime Dağılımı:")
    for keyword, count in stats['keyword_distribution'].items():
        percentage = stats['keyword_percentages'][keyword]
        print(f"  - {keyword}: {count} metin ({percentage:.1f}%)")


def example_4_from_file():
    """Örnek 4: Dosyadan anahtar kelime yükleme"""
    print("\n" + "="*60)
    print("ÖRNEK 4: DOSYADAN ANAHTAR KELİME YÜKLEME")
    print("="*60)
    
    # Anahtar kelimeleri dosyadan yükle
    keywords_file = "keywords.txt"
    
    try:
        keywords = KeywordLoader.load_from_file(keywords_file)
        print(f"\n{keywords_file} dosyasından yüklenen kelimeler:")
        for i, keyword in enumerate(keywords, 1):
            print(f"  {i}. {keyword}")
        
        # Matcher oluştur
        matcher = KeywordMatcher(keywords)
        
        # Örnek analiz
        text = "Deprem sonrası yardım çalışmaları ve enkaz kaldırma operasyonları."
        result = matcher.categorize_text(text)
        
        print(f"\nÖrnek Metin: {text}")
        print(f"Bulunan Kelimeler: {result['matched_keywords']}")
        
    except FileNotFoundError:
        print(f"\n✗ {keywords_file} dosyası bulunamadı!")
        print("Lütfen önce keywords.txt dosyasını oluşturun.")


def example_5_save_keywords():
    """Örnek 5: Anahtar kelimeleri dosyaya kaydetme"""
    print("\n" + "="*60)
    print("ÖRNEK 5: ANAHTAR KELİMELERİ KAYDETME")
    print("="*60)
    
    # Örnek anahtar kelimeler
    keywords = [
        "deprem", "afet", "yardım", "enkaz", "kurtarma",
        "yıkım", "kayıp", "hastane", "barınak", "koordinasyon"
    ]
    
    output_file = "test_keywords.txt"
    
    print(f"\n{len(keywords)} anahtar kelime {output_file} dosyasına kaydediliyor...")
    
    KeywordLoader.save_to_file(keywords, output_file)
    
    print(f"✓ Başarıyla kaydedildi: {output_file}")


def example_6_full_workflow():
    """Örnek 6: Tam iş akışı simülasyonu"""
    print("\n" + "="*60)
    print("ÖRNEK 6: TAM İŞ AKIŞI SİMÜLASYONU")
    print("="*60)
    
    # 1. Anahtar kelimeleri yükle
    keywords = [
        "deprem", "afet", "yardım", "enkaz", "kurtarma",
        "yıkım", "kayıp", "hastane", "barınak", "koordinasyon"
    ]
    
    print("\n1. Anahtar Kelimeler:")
    print(f"   {', '.join(keywords)}")
    
    # 2. Örnek veri seti oluştur
    sample_data = [
        {
            'ID': 1,
            'text': 'Deprem sonrası enkaz kaldırma çalışmaları başladı.',
            'AOD': 'ÇH'
        },
        {
            'ID': 2,
            'text': 'Yardım malzemeleri bölgeye ulaştırılıyor.',
            'AOD': 'ÇH'
        },
        {
            'ID': 3,
            'text': 'Hastanelerde tedaviler sürüyor.',
            'AOD': 'ÇH'
        },
        {
            'ID': 4,
            'text': 'Normal bir gün, özel bir şey yok.',
            'AOD': 'DİĞER'
        }
    ]
    
    print(f"\n2. Örnek Veri: {len(sample_data)} kayıt")
    
    # 3. AOD='ÇH' olanları filtrele
    filtered = [d for d in sample_data if d['AOD'] == 'ÇH']
    print(f"\n3. Filtreleme: {len(filtered)} kayıt (AOD='ÇH')")
    
    # 4. Kategorize et
    matcher = KeywordMatcher(keywords)
    
    print("\n4. Kategorizasyon Sonuçları:")
    print("-" * 60)
    
    for item in filtered:
        result = matcher.categorize_text(item['text'])
        print(f"\nID {item['ID']}: {item['text'][:50]}...")
        print(f"  Anahtar Kelimeler: {result['matched_keywords']}")
        print(f"  Toplam: {result['keyword_count']} kelime")
    
    # 5. Genel istatistikler
    texts = [d['text'] for d in filtered]
    stats = matcher.get_statistics(texts)
    
    print("\n5. Genel İstatistikler:")
    print("-" * 60)
    print(f"  Eşleşme Oranı: {stats['match_rate']:.2f}%")
    print(f"  En Çok Geçen Kelimeler:")
    for keyword, count in sorted(
        stats['keyword_distribution'].items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:5]:
        print(f"    - {keyword}: {count}")


def main():
    """Tüm örnekleri çalıştır"""
    print("\n" + "="*60)
    print("DEPREM VERİLERİ KATEGORİZASYON SİSTEMİ")
    print("ÖRNEK KULLANIM SCRIPTLERI")
    print("="*60)
    
    examples = [
        ("Metin İşleme", example_1_text_processing),
        ("Anahtar Kelime Eşleştirme", example_2_keyword_matching),
        ("Çoklu Metin Analizi", example_3_multiple_texts),
        ("Dosyadan Yükleme", example_4_from_file),
        ("Dosyaya Kaydetme", example_5_save_keywords),
        ("Tam İş Akışı", example_6_full_workflow),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        try:
            func()
        except Exception as e:
            print(f"\n✗ Örnek {i} çalıştırılırken hata: {e}")
    
    print("\n" + "="*60)
    print("TÜM ÖRNEKLER TAMAMLANDI")
    print("="*60)


if __name__ == "__main__":
    main()

