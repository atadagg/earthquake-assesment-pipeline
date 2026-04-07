import sys
from pathlib import Path

# Make the extractors package importable
sys.path.insert(0, str(Path(__file__).parent.parent / "extractors"))

from address_extractor import AddressExtractor

# ── helpers ────────────────────────────────────────────────────────────────────

passed = 0
failed = 0

def check(label: str, text: str, expected: str):
    global passed, failed
    result = AddressExtractor.extract_address(text)
    ok = result == expected
    status = "✓" if ok else "✗"
    print(f"  {status} {label}")
    if not ok:
        print(f"      input   : {text}")
        print(f"      expected: {expected}")
        print(f"      got     : {result}")
        failed += 1
    else:
        passed += 1

def check_contains(label: str, text: str, substring: str):
    """Pass if the result contains the expected substring."""
    global passed, failed
    result = AddressExtractor.extract_address(text)
    ok = substring in result
    status = "✓" if ok else "✗"
    print(f"  {status} {label}")
    if not ok:
        print(f"      input    : {text}")
        print(f"      must have: {substring}")
        print(f"      got      : {result}")
        failed += 1
    else:
        passed += 1

def check_not_detected(label: str, text: str):
    check(label, text, "ADDRESS NOT DETECTED")

# ── test groups ────────────────────────────────────────────────────────────────

def test_city_only():
    print("\n── City only ──")
    check("plain city name",
          "İstanbul'da büyük bir deprem oldu.",
          "İSTANBUL")
    check("city with suffix (ablative)",
          "Ankara'dan yardım ekipleri yola çıktı.",
          "ANKARA")
    check("city with suffix (locative)",
          "İzmir'de hasar çok fazla.",
          "İZMİR")

def test_city_and_valid_district():
    print("\n── City + valid district ──")
    check("İstanbul + Kadıköy (valid)",
          "İstanbul Kadıköy'de bina çöktü.",
          "İSTANBUL / KADIKÖY")
    check("Ankara + Çankaya (valid)",
          "Ankara Çankaya bölgesinde hasar var.",
          "ANKARA / ÇANKAYA")
    check("İzmir + Bornova (valid)",
          "İzmir Bornova'da enkaz kaldırma çalışması sürüyor.",
          "İZMİR / BORNOVA")

def test_district_from_wrong_city():
    print("\n── District belongs to a different city → drop district ──")
    # Kadıköy is in İstanbul, not in Ankara
    check("Ankara + Kadıköy (invalid pair → city only)",
          "Ankara Kadıköy civarında deprem hissedildi.",
          "ANKARA")

def test_neighbourhood_and_street():
    print("\n── Neighbourhood / street ──")
    check_contains("neighbourhood keyword",
                   "Bağcılar Mahallesi'nde bina hasar gördü.",
                   "Bağcılar Mahallesi")
    check_contains("street keyword",
                   "Atatürk Caddesi üzerindeki binalar yıkıldı.",
                   "Atatürk Caddesi")
    check_contains("sokak keyword",
                   "Çiçek Sokak No 5'teki apartman çöktü.",
                   "Çiçek Sokak")

def test_full_address():
    print("\n── Full address (city + district + neighbourhood + street) ──")
    result = AddressExtractor.extract_address(
        "İstanbul Kadıköy Moda Mahallesi Bahariye Caddesi No 12 enkaz altında kişiler var."
    )
    print(f"  full address result: {result}")
    assert "İSTANBUL" in result, f"Expected İSTANBUL in: {result}"
    assert "KADIKÖY"  in result, f"Expected KADIKÖY in: {result}"
    assert "Moda Mahallesi" in result, f"Expected neighbourhood in: {result}"
    assert "Bahariye Caddesi" in result, f"Expected street in: {result}"
    print("  ✓ full address")
    global passed
    passed += 1

def test_building_number():
    print("\n── Building number ──")
    check_contains("valid door number",
                   "İstanbul Kadıköy Moda Mahallesi No 7",
                   "No 7")
    check_contains("daire number",
                   "Ankara Çankaya Kızılay Sokak Daire 3",
                   "Daire 3")

def test_not_detected():
    print("\n── ADDRESS NOT DETECTED cases ──")
    check_not_detected("empty string", "")
    check_not_detected("no address info",
                       "Bugün hava çok güzeldi, pikniğe gittik.")
    check_not_detected("noise keywords only",
                       "Muhtara bilgi verildi, resmi açıklama bekleniyor.")

# ── run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  AddressExtractor Tests")
    print("=" * 55)

    test_city_only()
    test_city_and_valid_district()
    test_district_from_wrong_city()
    test_neighbourhood_and_street()
    test_full_address()
    test_building_number()
    test_not_detected()

    print("\n" + "=" * 55)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 55)

    sys.exit(1 if failed > 0 else 0)