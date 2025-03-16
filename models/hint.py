import logging
import unicodedata


class Hint:
    def __init__(self, text):
        self.text = text
        self.logger = logging.getLogger("hint")

    def sanitize(self):
        self.text = self.text.replace("œ", "oe").replace("'", "").strip()
        self.text = self._remove_accents(self.text)
        return self

    def _remove_accents(self, text):
        return "".join(
            c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
        )

    def __str__(self):
        return f"{self.text}"

    def __repr__(self):
        return f"{self.text}"
