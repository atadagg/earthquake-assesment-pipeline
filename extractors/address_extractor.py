"""
address_extractor.py

Usage:
    from address_extractor import AddressExtractor

    result = AddressExtractor.extract_address("Hatay Antakya Armutlu mah Atatürk cad no 12")
    print(result)
"""

import requests
from transformers import pipeline

# ── CONFIG ────────────────────────────────────────────────────────────────────

NER_MODEL_DIR  = "./ner_model"          # path to your copied model folder
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"  # replace with your key
GEOCODE_URL    = "https://maps.googleapis.com/maps/api/geocode/json"
FIELD_ORDER    = ["IL", "ILCE", "MAHALLE", "SOKAK", "APARTMAN", "BINA", "DAIRE", "POI"]


class AddressExtractor:

    _nlp = None  # model loaded once, shared across all calls

    @classmethod
    def _get_nlp(cls):
        if cls._nlp is None:
            cls._nlp = pipeline(
                "ner",
                model=NER_MODEL_DIR,
                tokenizer=NER_MODEL_DIR,
                aggregation_strategy="simple",
            )
        return cls._nlp

    @staticmethod
    def _entities_to_addresses(entities: list[dict]) -> list[str]:
        """Split flat NER entity list into separate address strings."""
        if not entities:
            return []

        groups = []
        current = {f: [] for f in FIELD_ORDER}

        for e in entities:
            tag = e["entity"].upper()
            if tag not in FIELD_ORDER:
                continue
            if current[tag]:  # repeated tag = new address starting
                groups.append(current)
                current = {f: [] for f in FIELD_ORDER}
            current[tag].append(e["value"])

        if any(current[f] for f in FIELD_ORDER):
            groups.append(current)

        result = []
        for group in groups:
            parts = [" ".join(group[f]) for f in FIELD_ORDER if group[f]]
            if parts:
                result.append(", ".join(parts))

        return result

    @staticmethod
    def _geocode(address: str) -> dict:
        """Call Google Maps and return lat, lng, formatted address."""
        if not address.strip():
            return {"formatted": None, "lat": None, "lng": None}

        try:
            resp = requests.get(
                GEOCODE_URL,
                params={
                    "address":  address + ", Türkiye",
                    "key":      GOOGLE_API_KEY,
                    "region":   "TR",
                    "language": "tr",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data["status"] != "OK" or not data["results"]:
                return {"formatted": address, "lat": None, "lng": None}

            loc = data["results"][0]["geometry"]["location"]
            return {
                "formatted": data["results"][0]["formatted_address"],
                "lat":       loc["lat"],
                "lng":       loc["lng"],
            }
        except Exception:
            return {"formatted": address, "lat": None, "lng": None}

    @classmethod
    def extract_address(cls, text: str) -> str:
        """
        Extract addresses from Turkish text and geocode them.

        Args:
            text: Raw Turkish text (earthquake message, social media post, etc.)

        Returns:
            A string with one line per address found:
            "Hatay, Antakya, Armutlu Mah. | LAT: 36.2021 | LNG: 36.1603"

            Returns "No address found." if nothing is detected.
        """
        nlp = cls._get_nlp()

        raw_entities = nlp(text)
        entities = [
            {"entity": e["entity_group"], "value": e["word"]}
            for e in raw_entities
        ]

        addresses = cls._entities_to_addresses(entities)

        if not addresses:
            return "No address found."

        lines = []
        for address in addresses:
            geo = cls._geocode(address)
            if geo["lat"] is not None:
                line = f"{geo['formatted']} | LAT: {geo['lat']} | LNG: {geo['lng']}"
            else:
                line = f"{address} | LAT: N/A | LNG: N/A"
            lines.append(line)

        return "\n".join(lines)


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_texts = [
        "Hatay Antakya Armutlu mah Atatürk cad no 12 enkaz altında yaralı var",
        "Bayraklı'daki Emrah Apartmanı'nda enkaz altında kalan kişiler var",
        "Ben Kahramanmaraş merkezde Carrefour'un arkasındayım, komşum da Dulkadiroğlu Fatih mahallesinde",
        "Lütfen yardım edin çok korkuyorum",
    ]

    for text in test_texts:
        print(f"INPUT : {text}")
        result = AddressExtractor.extract_address(text)
        print(f"OUTPUT: {result}")
        print()