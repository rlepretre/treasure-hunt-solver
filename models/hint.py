import logging
import unicodedata


class Hint:
    def __init__(self, text):
        self.text = text
        self.logger = logging.getLogger("hint")

    def sanitize(self):
        self.text = self.text.replace("œ", "oe").replace("'", "").strip()
        self.text = self._remove_accents(self.text)
        return self.text

    def _remove_accents(text):
        return "".join(
            c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
        )

    def __str__(self):
        return f"{self.text} ({self.confidence:.2f})"

    def __repr__(self):
        return f"{self.text} ({self.confidence:.2f})"
