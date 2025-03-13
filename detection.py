import logging
import unicodedata


class Detection:
    def __init__(self, ocr_result):
        self.text = ocr_result[1]
        self.confidence = ocr_result[2]
        self.logger = logging.getLogger("detection")

    def sanitize(self):
        self.text = self.text.replace("0", "").replace("@", "").replace("œ", "oe").replace("'", "").strip()
        return self.text

    def _remove_accents(text):
        return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")

    def __str__(self):
        return f"{self.text} ({self.confidence:.2f})"

    def __repr__(self):
        return f"{self.text} ({self.confidence:.2f})"
