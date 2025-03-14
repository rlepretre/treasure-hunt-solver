import logging
import re


class Coordinates:
    def __init__(self, ocr_result):
        self.coords_pair = self._sanitize(ocr_result)
        self.x = None
        self.y = None
        self.logger = logging.getLogger("coordinates")
        self._split_coordinates()

    def _split_coordinates(self):
        pattern = r"(-?\d{1,2}),(-?\d{1,2})"

        match = re.search(pattern, self.coords_pair)

        if match:
            self.x, self.y = match.groups()
            self.logger.info(f"Valid coordinates format: {self.x},{self.y}")
            return True
        else:
            self.logger.warning(f"Invalid coordinates format: {self.coords_pair}")
            return False

    def are_valid(self):
        pattern = r"^-?\d{1,2}$"
        return re.match(pattern, self.x) and re.match(pattern, self.y)

    def get_coords(self):
        return self.x, self.y

    @staticmethod
    def _sanitize(ocr_result):
        return ocr_result[0][1].replace("~", "-").replace(" ", "")

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return f"({self.x}, {self.y})"
