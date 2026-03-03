"""
Test Scripti
Kategorizasyon sisteminin tüm bileşenlerini test eder.
"""

import sys
from pathlib import Path

# Test sonuçları
test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}


def test_text_processor():
    """Text processor modülünü test et"""
    print("\n" + "="*60)
    print("TEST 1: TEXT PROCESSOR")
    print("="*60)
    
    try:
        from text_processor import TurkishTextProcessor
        
        processor = TurkishTextProcessor()
        
        # Test 1: Türkçe küçük harf
        test_text = "İSTANBUL"
        result = processor.turkish_lower(test_text)
        assert result == "istanbul", f"Beklenen: 'istanbul', Alınan: '{result}'"
        print("✓ Türkçe küçük harf dönüşümü: BAŞARILI")
        
        # Test 2: Türkçe büyük harf
        test_text = "istanbul"
        result = processor.turkish_upper(test_text)
        assert result == "İSTANBUL", f"Beklenen: 'İSTANBUL', Alınan: '{result}'"
        print("✓ Türkçe büyük harf dönüşümü: BAŞARILI")
        
        # Test 3: Metin temizleme
        test_text = "  Çok   fazla    boşluk  "
        result = processor.clean_text(test_text)
        assert result == "Çok fazla boşluk", f"Beklenen: 'Çok fazla boşluk', Alınan: '{result}'"
        print("✓ Metin temizleme: BAŞARILI")
        
        # Test 4: Cümle ayırma
        test_text = "Bu bir cümle. Bu da başka bir cümle!"
        result = processor.split_sentences(test_text)
        assert len(result) >= 2, f"En az 2 cümle bekleniyor, {len(result)} bulundu"
        print(f"✓ Cümle ayırma: BAŞARILI ({len(result)} cümle)")
        
        # Test 5: Kelime tokenizasyonu
        test_text = "Deprem sonrası yardım çalışmaları"
        result = processor.tokenize_words(test_text)
        assert len(result) >= 3, f"En az 3 kelime bekleniyor, {len(result)} bulundu"
        print(f"✓ Kelime tokenizasyonu: BAŞARILI ({len(result)} kelime)")
        
        test_results['passed'] += 1
        print("\n✓✓✓ TEXT PROCESSOR TESTLERİ BAŞARILI ✓✓✓")
        return True
        
    except Exception as e:
        test_results['failed'] += 1
        test_results['errors'].append(f"Text Processor: {str(e)}")
        print(f"\n✗✗✗ TEXT PROCESSOR TESTLERİ BAŞARISIZ: {e} ✗✗✗")
        return False


def test_keyword_matcher():
    """Keyword matcher modülünü test et"""
    print("\n" + "="*60)
    print("TEST 2: KEYWORD MATCHER")
    print("="*60)
    
    try:
        from keyword_matcher import KeywordMatcher, KeywordLoader
        
        # Test anahtar kelimeleri
        keywords = ["deprem", "afet", "yardım", "enkaz", "kurtarma"]
        
        matcher = KeywordMatcher(keywords)
        
        # Test 1: Anahtar kelime eşleştirme
        test_text = "Deprem sonrası enkaz kaldırma çalışmaları başladı."
        matches = matcher.match_keywords(test_text)
        assert matches['deprem'] == True, "Deprem kelimesi bulunmalı"
        assert matches['enkaz'] == True, "Enkaz kelimesi bulunmalı"
        print("✓ Anahtar kelime eşleştirme: BAŞARILI")
        
        # Test 2: Frekans sayma
        test_text = "Deprem sonrası deprem bölgesinde enkaz var."
        counts = matcher.match_keywords_with_count(test_text)
        assert counts['deprem'] >= 2, f"Deprem 2 kez geçmeli, {counts['deprem']} bulundu"
        print(f"✓ Frekans sayma: BAŞARILI (deprem: {counts['deprem']})")
        
        # Test 3: Eşleşen kelime listesi
        matched = matcher.get_matched_keywords(test_text)
        assert 'deprem' in matched, "Deprem listede olmalı"
        assert 'enkaz' in matched, "Enkaz listede olmalı"
        print(f"✓ Eşleşen kelime listesi: BAŞARILI ({len(matched)} kelime)")
        
        # Test 4: Tam kategorizasyon
        result = matcher.categorize_text(test_text)
        assert 'matched_keywords' in result, "Sonuçta matched_keywords olmalı"
        assert result['keyword_count'] >= 2, "En az 2 anahtar kelime bulunmalı"
        print(f"✓ Tam kategorizasyon: BAŞARILI ({result['keyword_count']} kelime)")
        
        # Test 5: İstatistikler
        texts = [
            "Deprem oldu, enkaz var.",
            "Yardım gerekiyor.",
            "Normal bir metin."
        ]
        stats = matcher.get_statistics(texts)
        assert stats['total_texts'] == 3, "3 metin olmalı"
        assert stats['texts_with_matches'] >= 2, "En az 2 metin eşleşmeli"
        print(f"✓ İstatistikler: BAŞARILI ({stats['texts_with_matches']}/{stats['total_texts']})")
        
        test_results['passed'] += 1
        print("\n✓✓✓ KEYWORD MATCHER TESTLERİ BAŞARILI ✓✓✓")
        return True
        
    except Exception as e:
        test_results['failed'] += 1
        test_results['errors'].append(f"Keyword Matcher: {str(e)}")
        print(f"\n✗✗✗ KEYWORD MATCHER TESTLERİ BAŞARISIZ: {e} ✗✗✗")
        return False


def test_keyword_loader():
    """Keyword loader fonksiyonlarını test et"""
    print("\n" + "="*60)
    print("TEST 3: KEYWORD LOADER")
    print("="*60)
    
    try:
        from keyword_matcher import KeywordLoader
        
        # Test 1: Dosyadan yükleme
        test_file = "keywords.txt"
        if Path(test_file).exists():
            keywords = KeywordLoader.load_from_file(test_file)
            assert len(keywords) > 0, "Anahtar kelime yüklenmeliydi"
            print(f"✓ Dosyadan yükleme: BAŞARILI ({len(keywords)} kelime)")
        else:
            print("⚠ keywords.txt bulunamadı, test atlanıyor")
        
        # Test 2: Listeden yükleme
        keyword_list = ["  deprem  ", "afet", "  yardım  "]
        keywords = KeywordLoader.load_from_list(keyword_list)
        assert len(keywords) == 3, f"3 kelime bekleniyor, {len(keywords)} bulundu"
        assert all(kw.strip() == kw for kw in keywords), "Kelimeler temizlenmeli"
        print("✓ Listeden yükleme: BAŞARILI")
        
        # Test 3: Dosyaya kaydetme
        test_keywords = ["test1", "test2", "test3"]
        test_output = "test_keywords_output.txt"
        KeywordLoader.save_to_file(test_keywords, test_output)
        
        if Path(test_output).exists():
            # Okunan kelimeleri kontrol et
            loaded = KeywordLoader.load_from_file(test_output)
            assert len(loaded) == 3, f"3 kelime bekleniyor, {len(loaded)} bulundu"
            print("✓ Dosyaya kaydetme: BAŞARILI")
            
            # Test dosyasını temizle
            Path(test_output).unlink()
            print("✓ Test dosyası temizlendi")
        else:
            raise Exception("Test dosyası oluşturulamadı")
        
        test_results['passed'] += 1
        print("\n✓✓✓ KEYWORD LOADER TESTLERİ BAŞARILI ✓✓✓")
        return True
        
    except Exception as e:
        test_results['failed'] += 1
        test_results['errors'].append(f"Keyword Loader: {str(e)}")
        print(f"\n✗✗✗ KEYWORD LOADER TESTLERİ BAŞARISIZ: {e} ✗✗✗")
        return False


def test_integration():
    """Entegrasyon testi - tüm modüller birlikte"""
    print("\n" + "="*60)
    print("TEST 4: ENTEGRASYON TESTİ")
    print("="*60)
    
    try:
        from text_processor import TurkishTextProcessor
        from keyword_matcher import KeywordMatcher
        
        # Sistem oluştur
        processor = TurkishTextProcessor()
        keywords = ["deprem", "afet", "yardım", "enkaz", "kurtarma"]
        matcher = KeywordMatcher(keywords)
        
        # Test metni
        raw_text = "  İSTANBUL'da DEPREM oldu! Enkaz altında insanlar var. YARDIM gerekiyor.  "
        
        # 1. Metin işleme
        cleaned_text = processor.clean_text(raw_text)
        normalized_text = processor.turkish_lower(cleaned_text)
        print(f"✓ Metin işlendi: {len(raw_text)} → {len(cleaned_text)} karakter")
        
        # 2. Cümlelere ayır
        sentences = processor.split_sentences(cleaned_text)
        print(f"✓ Cümlelere ayrıldı: {len(sentences)} cümle")
        
        # 3. Kategorize et
        result = matcher.categorize_text(normalized_text)
        print(f"✓ Kategorize edildi: {result['keyword_count']} anahtar kelime")
        print(f"  Bulunan: {', '.join(result['matched_keywords'])}")
        
        # 4. Doğrulama
        assert result['keyword_count'] >= 3, "En az 3 anahtar kelime bulunmalı"
        assert 'deprem' in result['matched_keywords'], "Deprem bulunmalı"
        assert 'enkaz' in result['matched_keywords'], "Enkaz bulunmalı"
        assert 'yardım' in result['matched_keywords'], "Yardım bulunmalı"
        
        test_results['passed'] += 1
        print("\n✓✓✓ ENTEGRASYON TESTİ BAŞARILI ✓✓✓")
        return True
        
    except Exception as e:
        test_results['failed'] += 1
        test_results['errors'].append(f"Entegrasyon: {str(e)}")
        print(f"\n✗✗✗ ENTEGRASYON TESTİ BAŞARISIZ: {e} ✗✗✗")
        return False


def print_summary():
    """Test özetini yazdır"""
    print("\n" + "="*60)
    print("TEST ÖZETİ")
    print("="*60)
    
    total = test_results['passed'] + test_results['failed']
    success_rate = (test_results['passed'] / total * 100) if total > 0 else 0
    
    print(f"\nToplam Test: {total}")
    print(f"Başarılı: {test_results['passed']} ✓")
    print(f"Başarısız: {test_results['failed']} ✗")
    print(f"Başarı Oranı: {success_rate:.1f}%")
    
    if test_results['errors']:
        print("\nHatalar:")
        for error in test_results['errors']:
            print(f"  ✗ {error}")
    
    print("\n" + "="*60)
    
    if test_results['failed'] == 0:
        print("🎉 TÜM TESTLER BAŞARIYLA GEÇTİ! 🎉")
    else:
        print("⚠️  BAZI TESTLER BAŞARISIZ OLDU ⚠️")
    
    print("="*60)


def main():
    """Ana test fonksiyonu"""
    print("\n" + "="*60)
    print("DEPREM VERİLERİ KATEGORİZASYON SİSTEMİ")
    print("TEST PAKETİ")
    print("="*60)
    
    # Testleri çalıştır
    tests = [
        test_text_processor,
        test_keyword_matcher,
        test_keyword_loader,
        test_integration
    ]
    
    for test_func in tests:
        try:
            test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Testler kullanıcı tarafından durduruldu")
            break
        except Exception as e:
            print(f"\n✗ Beklenmeyen hata: {e}")
            test_results['failed'] += 1
            test_results['errors'].append(f"Beklenmeyen: {str(e)}")
    
    # Özeti göster
    print_summary()
    
    # Çıkış kodu
    sys.exit(0 if test_results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()

