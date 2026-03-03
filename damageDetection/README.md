# Deprem Verileri Kategorizasyon Sistemi

Bu klasör, 6 Şubat 2023 Kahramanmaraş depremi sonrası Ekşi Sözlük'ten çekilen verileri kategorilendirmek için geliştirilmiş Python scriptlerini içerir.

## Dosya Yapısı

```
kerem/
├── README.md                           # Bu dosya
├── requirements.txt                    # Python bağımlılıkları
├── keywords.txt                        # 10 anahtar kelime listesi
├── text_processor.py                   # Türkçe metin işleme modülü
├── keyword_matcher.py                  # Anahtar kelime eşleştirme modülü
├── categorize_earthquake_data.py       # Ana kategorizasyon scripti
└── example_usage.py                    # Örnek kullanım scriptleri
```

## Kurulum

### 1. Gereksinimler

Python 3.7 veya üzeri gereklidir.

### 2. Bağımlılıkları Yükleme

```
cd damageDetection
pip install -r requirements.txt
```

## Kullanım

### Temel Kullanım

```bash
python categorize_earthquake_data.py --input data.xlsx --output results.csv
```

### Parametreler

- `--input`: Girdi Excel dosyası (zorunlu)
- `--keywords`: Anahtar kelime dosyası (varsayılan: keywords.txt)
- `--output`: Çıktı CSV dosyası (varsayılan: categorized_results.csv)
- `--stats`: İstatistik JSON dosyası (varsayılan: statistics.json)
- `--aod-filter`: AOD filtre değeri (varsayılan: ÇH)

### Örnekler

#### Örnek 1: Varsayılan parametrelerle

```bash
python categorize_earthquake_data.py --input ../data/deprem_verileri.xlsx
```

#### Örnek 2: Özel çıktı dosyaları

```bash
python categorize_earthquake_data.py \
    --input ../data/deprem_verileri.xlsx \
    --output sonuclar.csv \
    --stats istatistikler.json
```

#### Örnek 3: Farklı anahtar kelimeler

```bash
python categorize_earthquake_data.py \
    --input ../data/deprem_verileri.xlsx \
    --keywords ozel_kelimeler.txt
```

## Modüller

### 1. text_processor.py

Türkçe metinleri işlemek için araçlar:
- Türkçe karakter dönüşümleri (İ/i, I/ı)
- Metin temizleme
- Cümle ayırma
- Kelime tokenizasyonu
- Durak kelime filtreleme

```python
from text_processor import TurkishTextProcessor

processor = TurkishTextProcessor()
text = "İSTANBUL'da deprem oldu."
lower_text = processor.turkish_lower(text)
words = processor.tokenize_words(text)
```

### 2. keyword_matcher.py

Anahtar kelime eşleştirme ve kategorizasyon:
- Metinlerde anahtar kelime arama
- Frekans hesaplama
- Kategorizasyon
- İstatistik üretme

```python
from keyword_matcher import KeywordMatcher

keywords = ["deprem", "afet", "yardım"]
matcher = KeywordMatcher(keywords)
result = matcher.categorize_text("Deprem sonrası yardım çalışmaları.")
```

### 3. categorize_earthquake_data.py

Ana kategorizasyon scripti:
- Excel dosyası okuma
- AOD filtreleme
- Toplu kategorizasyon
- Sonuç kaydetme

## Anahtar Kelimeler

Varsayılan 10 anahtar kelime (`keywords.txt`):

1. deprem
2. afet
3. yardım
4. enkaz
5. kurtarma
6. yıkım
7. kayıp
8. hastane
9. barınak
10. koordinasyon

### Anahtar Kelime Dosyası Formatı

```
# Yorum satırı
deprem
afet
yardım
```

## Çıktı Formatları

### CSV Çıktısı (categorized_results.csv)

```csv
ID,filename,text,label,AOD,matched_keywords,keyword_count,kategori_deprem,kategori_afet,...
1,file1.txt,"Deprem oldu",label1,ÇH,"['deprem']",1,True,False,...
```

### JSON İstatistikleri (statistics.json)

```json
{
  "total_texts": 1000,
  "texts_with_matches": 850,
  "match_rate": 85.0,
  "keyword_distribution": {
    "deprem": 450,
    "yardım": 320
  }
}
```

## Örnek Kullanım Scriptleri

Örnek kullanımları görmek için:

```bash
python example_usage.py
```

Bu script şunları gösterir:
1. Temel metin işleme
2. Anahtar kelime eşleştirme
3. Çoklu metin analizi
4. Dosyadan yükleme
5. Dosyaya kaydetme
6. Tam iş akışı

## İş Akışı

```
Excel Dosyası
    ↓
[1] Dosya Yükleme
    ↓
[2] AOD='ÇH' Filtreleme
    ↓
[3] Text Alanı Çıkarma
    ↓
[4] Metin Normalizasyonu
    ↓
[5] Anahtar Kelime Eşleştirme
    ↓
[6] Kategorizasyon
    ↓
[7] CSV + JSON Çıktısı
```

## Corpus Entegrasyonu

Bu sistem, mevcut Corpus-Earthquake projesindeki araçlarla uyumlu çalışır:

### Java Sınıfları (Opsiyonel)
- `Corpus.java`: Metin korpusu yönetimi
- `TurkishSplitter.java`: Türkçe cümle ayırma
- `Sentence.java`: Cümle yapısı

### Python Scriptleri
- `../ata/unique_words.py`: Kelime frekans analizi
- `../ata/combine_data.py`: Veri birleştirme
- `../ata/uppercaser.py`: Türkçe karakter dönüşümü

## Troubleshooting

### Hata: Excel dosyası bulunamadı
```bash
# Dosya yolunu kontrol edin
ls -la ../data/deprem_verileri.xlsx
```

### Hata: AOD sütunu bulunamadı
Excel dosyanızda şu sütunlar olmalı:
- ID
- filename
- text
- label
- AOD

### Hata: Anahtar kelime dosyası boş
```bash
# keywords.txt dosyasını kontrol edin
cat keywords.txt
```

## Geliştirme

### Yeni Anahtar Kelime Ekleme

1. `keywords.txt` dosyasını düzenleyin
2. Her satırda bir anahtar kelime
3. Toplam 10 kelime olmalı

### Özel Metin İşleme

`text_processor.py` modülünü özelleştirin:

```python
class CustomTextProcessor(TurkishTextProcessor):
    def custom_clean(self, text):
        # Özel temizleme mantığı
        return text
```

## Notlar

- Türkçe karakter duyarlılığı: i/İ, ı/I dönüşümleri otomatik
- Anahtar kelimeler küçük harfe dönüştürülür
- Noktalama işaretleri korunur (isteğe bağlı temizlik)
- CSV çıktısı UTF-8-BOM formatında (Excel uyumlu)

## Lisans

Bu proje, ana Corpus-Earthquake projesiyle aynı lisans altındadır.

## İletişim

Sorularınız için proje sahibi ile iletişime geçin.

---

**Son Güncelleme:** Kasım 2025
**Versiyon:** 1.0

