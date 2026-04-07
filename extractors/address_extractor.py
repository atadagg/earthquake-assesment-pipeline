import json
import re
from collections import defaultdict
from pathlib import Path


def _tr_upper(text: str) -> str:
    """Turkish-aware uppercase conversion."""
    return text.replace('i', 'İ').replace('ı', 'I').upper()


def _tr_lower(text: str) -> str:
    """Turkish-aware lowercase conversion."""
    return text.replace('İ', 'i').replace('I', 'ı').lower()


def _normalize(token: str) -> str:
    """
    Strips common Turkish noun suffixes used in addresses so that
    e.g. 'Ankara'dan' → 'ANKARA', 'Kadıköy'de' → 'KADIKÖY'.
    The raw uppercase form is always tried first — suffixes are only
    stripped when the raw form does not match a known city/district.
    """
    suffixes = [
        "NİN", "NUN", "NÜN", "NIN",   # genitive
        "NDA", "NDE",                   # locative with buffer
        "DAN", "DEN", "TAN", "TEN",    # ablative
        "DA", "DE", "TA", "TE",        # locative
        "YA", "YE",                    # dative
        "YI", "Yİ", "YU", "YÜ",       # accusative
        "IN", "İN", "UN", "ÜN",       # genitive short
    ]
    upper = _tr_upper(token)
    for suffix in suffixes:
        if upper.endswith(suffix) and len(upper) - len(suffix) >= 3:
            return upper[: len(upper) - len(suffix)]
    return upper


def _normalize_try_raw_first(token: str, cities: set, all_districts: set) -> str:
    """
    Returns the raw uppercase form if it matches a known city/district,
    otherwise falls back to suffix-stripped form.
    This prevents 'Çankaya' → 'ÇANKAY' when ÇANKAYA is a valid district.
    """
    upper = _tr_upper(token)
    if upper in cities or upper in all_districts:
        return upper
    return _normalize(token)

class AddressExtractor:
    CITIES: set = set()
    DISTRICTS: defaultdict = defaultdict(set)

    # Regex for Neighborhood
    MAH_REGEX = r"(?i)([a-zçğıöşüA-ZÇĞİÖŞÜ0-9\s\-]{2,30}?)\s+(Mahallesi|Mah\.|Mah|Mh\.|Mh)(?![a-zçğıöşüA-ZÇĞİÖŞÜ])"

    # Regex for Street, Avenue, Boulevard, Apartment, Site
    YOL_REGEX = r"(?i)([a-zçğıöşüA-ZÇĞİÖŞÜ0-9\.\s\-]{2,40})\s+(Sokak|Sok\.|Sk\.|Sk|Caddesi|Cad\.|Cd\.|Bulvarı|Bul\.|Yolu|Apartmanı|Apt\.|Apt|Sitesi|Sit\.)(?![a-zçğıöşüA-ZÇĞİÖŞÜ])"

    # Regex for Door / Floor / Flat numbers
    NO_REGEX = r"(?i)\b(No|Kapı|Daire|Kat|D\.|K\.|D:|K:)[:\.\s]*([0-9]+)"

    @classmethod
    def load_turkey_data(cls, json_path: str) -> None:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data_array = json.load(f)

            cls.CITIES.clear()
            cls.DISTRICTS.clear()

            for obj in data_array:
                city_name     = _tr_upper(obj.get("sehir_adi", ""))
                district_name = _tr_upper(obj.get("ilce_adi", ""))
                cls.CITIES.add(city_name)
                cls.DISTRICTS[city_name].add(district_name)

        except FileNotFoundError:
            print(f"File not found: {json_path}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {json_path}")

    @classmethod
    def extract_address(cls, text: str) -> str:
        # Normalise whitespace / newlines
        clean_text = re.sub(r"[\r\n]+", " ", text)

        # ------------------------------------------------------------------
        # Step 1 — Regex-based structural components (neighbourhood, street,
        #           building number).  These are extracted first because they
        #           are the most reliable signal and do not depend on knowing
        #           the city/district beforehand.
        # ------------------------------------------------------------------
        mahalle_match = cls._regex_find_full(clean_text, cls.MAH_REGEX)
        yollar        = cls._regex_find_all_full(clean_text, cls.YOL_REGEX)
        no_raw        = cls._regex_find_full(clean_text, cls.NO_REGEX)
        no_val        = cls._regex_find_group(clean_text, cls.NO_REGEX, 2)

        structural_found = bool(mahalle_match or yollar)

        # ------------------------------------------------------------------
        # Step 2 — City & district detection via token scanning.
        # ------------------------------------------------------------------
        tokens = re.split(r"[^a-zA-ZçğıöşüÇĞİÖŞÜ]+", clean_text)

        # Build a flat set of all district names for fast raw-form lookup
        all_districts: set = {d for districts in cls.DISTRICTS.values() for d in districts}

        found_city = None
        found_district = None
        district_candidate = None
        district_candidate_city = None

        for token in tokens:
            if len(token) < 3:
                continue

            # Use raw form first — only strip suffixes if raw form is unknown
            root = _normalize_try_raw_first(token, cls.CITIES, all_districts)

            # City match
            if root in cls.CITIES:
                found_city = root
                continue

            # District candidate
            if district_candidate is None:
                for city, districts in cls.DISTRICTS.items():
                    if root in districts:
                        district_candidate = root
                        district_candidate_city = city
                        break

        # ------------------------------------------------------------------
        # Step 3 — Validate city / district combination.
        # ------------------------------------------------------------------
        if district_candidate:
            if found_city:
                if district_candidate in cls.DISTRICTS.get(found_city, set()):
                    found_district = district_candidate
                # else: district belongs to a different city → drop it
            else:
                found_city = district_candidate_city
                found_district = district_candidate

        # ------------------------------------------------------------------
        # Step 4 — Assemble the result parts in order:
        #           City / District - Neighbourhood, Street, No
        # ------------------------------------------------------------------
        address_parts: list[str] = []

        if found_city:
            address_parts.append(found_city)
        if found_district:
            if address_parts:
                address_parts[-1] += f" / {found_district}"
            else:
                address_parts.append(found_district)

        # Neighbourhood
        if mahalle_match and cls._is_valid_match(mahalle_match, bool(found_city or found_district), structural_found):
            address_parts.append(f"- {mahalle_match}")

        # Streets / roads / buildings
        for yol in yollar:
            if cls._is_valid_match(yol, bool(found_city or found_district), structural_found):
                address_parts.append(yol)

        # Door / flat number
        if no_raw and cls._is_valid_number(no_val):
            address_parts.append(no_raw)

        # ------------------------------------------------------------------
        # Step 5 — Build the final string
        # ------------------------------------------------------------------
        result = ""
        for i, part in enumerate(address_parts):
            if i == 0:
                result += part
            elif part.startswith("- "):
                result += f" {part}"
            else:
                result += f", {part}"

        if len(result) < 3 or re.match(r"^, No.*", result):
            return "ADDRESS NOT DETECTED"

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_number(number_str: str) -> bool:
        if not number_str:
            return False
        try:
            int(number_str)
            if number_str.startswith("0"):
                return False
            if len(number_str) > 4:
                return False
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_match(match: str, city_found: bool, structural_found: bool) -> bool:
        """
        Accept a regex match if:
        - it does not contain noise words
        - a city/district was found (high confidence), OR
        - at least one other structural component was found (neighbourhood/street), OR
        - the match itself is short (≤ 4 words) to avoid false positives
        """
        if not match:
            return False

        lower = _tr_lower(match)
        invalid_keywords = ["muhtar", "yardım", "resmi", "bilgi"]
        if any(kw in lower for kw in invalid_keywords):
            return False

        if city_found or structural_found:
            return True

        return len(match.split()) <= 4

    @staticmethod
    def _regex_find_full(text: str, regex: str):
        m = re.search(regex, text)
        return m.group(0).strip() if m else None

    @staticmethod
    def _regex_find_group(text: str, regex: str, group_index: int):
        m = re.search(regex, text)
        if not m:
            return None
        try:
            return m.group(group_index).strip()
        except IndexError:
            return None

    @staticmethod
    def _regex_find_all_full(text: str, regex: str) -> list:
        return [m.group(0).strip() for m in re.finditer(regex, text)]


# Load data on module import
AddressExtractor.load_turkey_data(str(Path(__file__).parent / "turkiye.json"))