import json
import re
from collections import defaultdict


class MorphologyHelper:
    @staticmethod
    def get_root_primary(token: str) -> str:
        """
        Placeholder for your Turkish NLP morphology helper.
        In Python, you might use a library like 'Zemberek-Python' or 'SnowballStemmer'.
        For now, this just returns the uppercase token.
        """
        # A naive uppercase conversion that handles Turkish 'i' and 'ı'
        return token.replace('i', 'İ').replace('ı', 'I').upper()


class AddressExtractor:
    CITIES = set()
    DISTRICTS = defaultdict(set)

    # Regex for Neighborhood
    MAH_REGEX = r"(?i)([a-zçğıöşüA-ZÇĞİÖŞÜ0-9\s-]{2,30}?)\s+(Mahallesi|Mah\.|Mah|Mh\.|Mh)(?![a-zçğıöşüA-ZÇĞİÖŞÜ])"

    # Regex for Street, Avenue, Boulevard, Apartment, Site
    YOL_REGEX = r"(?i)([a-zçğıöşüA-ZÇĞİÖŞÜ0-9\.\s-]{2,30}?)\s+(Sokak|Sok\.|Sk\.|Sk|Caddesi|Cad\.|Cd\.|Bulvarı|Bul\.|Yolu|Apartmanı|Apt\.|Apt|Sitesi|Sit\.)(?![a-zçğıöşüA-ZÇĞİÖŞÜ])"

    # Regex for Door/Floor/Flat numbers
    NO_REGEX = r"(?i)\b(No|Kapı|Daire|Kat|D\.|K\.|D:|K:)[:\.\s]*([0-9]+)"

    @classmethod
    def load_turkey_data(cls, json_path: str):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data_array = json.load(f)

            for obj in data_array:
                # Custom upper to handle Turkish characters
                city_name = obj.get("sehir_adi", "").replace('i', 'İ').replace('ı', 'I').upper()
                district_name = obj.get("ilce_adi", "").replace('i', 'İ').replace('ı', 'I').upper()

                cls.CITIES.add(city_name)
                cls.DISTRICTS[city_name].add(district_name)
        except FileNotFoundError:
            print(f"File not found: {json_path}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {json_path}")

    @classmethod
    def extract_address(cls, text: str) -> str:
        # Replace newlines with spaces
        clean_text = re.sub(r'[\r\n]+', ' ', text)

        # Split by anything that isn't a Turkish or standard English letter
        tokens = re.split(r'[^a-zA-ZçğıöşüÇĞİÖŞÜ]+', clean_text)

        found_city = None
        found_district = None
        address_parts = []

        # 1. NLP-based City and District detection
        for token in tokens:
            if len(token) < 3:
                continue

            root = MorphologyHelper.get_root_primary(token)

            if root in cls.CITIES:
                found_city = root

            if found_city:
                if root in cls.DISTRICTS.get(found_city, set()):
                    found_district = root
            else:
                for city, districts in cls.DISTRICTS.items():
                    if root in districts:
                        found_district = root
                        found_city = city
                        break

        found_city_or_dist = bool(found_city or found_district)

        if found_city:
            address_parts.append(found_city)
        if found_district:
            # If city is already in the list, we append " / district" to the last item
            # Otherwise, just add district
            if address_parts:
                address_parts[-1] += f" / {found_district}"
            else:
                address_parts.append(f" / {found_district}")

        # 2. Regex-based Neighborhood and Street detection
        mahalle_match = cls._regex_find_full(clean_text, cls.MAH_REGEX)
        if cls._is_valid_match(mahalle_match, found_city_or_dist):
            address_parts.append(f"- {mahalle_match}")

        yollar = cls._regex_find_all_full(clean_text, cls.YOL_REGEX)
        for yol in yollar:
            if cls._is_valid_match(yol, found_city_or_dist):
                address_parts.append(yol)

        # 3. Number Filtering
        no_raw = cls._regex_find_full(clean_text, cls.NO_REGEX)
        no_val = cls._regex_find_group(clean_text, cls.NO_REGEX, 2)

        if no_raw and cls._is_valid_number(no_val):
            address_parts.append(no_raw)

        # Construct final string
        # Java used StringBuilder, we'll join our parts with comma spaces
        # Note: formatting slightly depends on how the Java string builder concatenated
        # Java did: City / District - Neighborhood, Street, No: 15

        result_builder = ""
        for i, part in enumerate(address_parts):
            if i == 0:
                result_builder += part
            elif part.startswith("- "):
                result_builder += f" {part}"
            else:
                result_builder += f", {part}"

        # Return error if result is too short or only contains "No"
        if len(result_builder) < 3 or re.match(r'^, No.*', result_builder):
            return "ADDRESS NOT DETECTED"

        return result_builder

    @staticmethod
    def _is_valid_number(number_obj: str) -> bool:
        if not number_obj:
            return False
        try:
            num = int(number_obj)

            # Rule 1: Starts with 0
            if number_obj.startswith("0"):
                return False

            # Rule 2: Longer than 4 digits
            if len(number_obj) > 4:
                return False

            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_match(match: str, city_found: bool) -> bool:
        if not match:
            return False

        # Custom lowercase to handle Turkish characters safely
        lower_match = match.replace('İ', 'i').replace('I', 'ı').lower()

        # Filter out irrelevant keywords
        invalid_keywords = ["muhtar", "yardım", "resmi", "bilgi"]
        if any(keyword in lower_match for keyword in invalid_keywords):
            return False

        if city_found:
            return True

        if len(match.split()) > 4:
            return False

        return True

    @staticmethod
    def _regex_find_full(text: str, regex: str) -> str:
        match = re.search(regex, text)
        return match.group(0).strip() if match else None

    @staticmethod
    def _regex_find_group(text: str, regex: str, group_index: int) -> str:
        match = re.search(regex, text)
        try:
            return match.group(group_index).strip() if match else None
        except IndexError:
            return None

    @staticmethod
    def _regex_find_all_full(text: str, regex: str) -> list:
        # re.finditer is used to get the full match strings like Matcher.find() in Java
        return [match.group(0).strip() for match in re.finditer(regex, text)]


# Initialize the data just like the static { loadTurkeyData(...) } block in Java
AddressExtractor.load_turkey_data("turkiye.json")
