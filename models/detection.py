import logging


class Detection:
    def __init__(self, ocr_result):
        self.text = ocr_result[1]
        self.confidence = ocr_result[2]
        self.box = ocr_result[0]
        self.logger = logging.getLogger("detection")

    def sanitize(self):
        # The location icon often gets detected as a 0 or @
        self.text = self.text.replace("0", "").replace("@", "").strip()
        return self

    def __str__(self):
        return f"{self.text} ({self.confidence:.2f})"

    def __repr__(self):
        return f"{self.text} ({self.confidence:.2f})"
