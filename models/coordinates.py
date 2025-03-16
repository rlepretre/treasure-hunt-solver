import logging
import math
import re


class Coordinates:
    def __init__(self, ocr_result=None, x=None, y=None):
        self.logger = logging.getLogger("coordinates")
        self.x: int = x
        self.y: int = y
        if ocr_result:
            self.coords_pair = self._sanitize(ocr_result)
            self._split_coordinates()

    def _split_coordinates(self):
        pattern = r"(-?\d{1,2}),(-?\d{1,2})"

        match = re.search(pattern, self.coords_pair)

        if match:
            x, y = match.groups()
            self.x = int(x)
            self.y = int(y)
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

    def get_distance(self, other):
        return math.sqrt((self.x - int(other.x)) ** 2 + (self.y - int(other.y)) ** 2)

    @staticmethod
    def _sanitize(ocr_result):
        return ocr_result[0][1].replace("~", "-").replace(" ", "")

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
