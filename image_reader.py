import logging
import math
import os

import cv2
import easyocr
import numpy as np

from models import Coordinates, Detection, Hint


class ImageReader:
    def __init__(self, image):
        self.image = image
        self.logger = logging.getLogger("image_reader")
        self.cropped_hunt_panel = None
        self.cropped_coords = None
        self.hint_box = None
        self.reader = easyocr.Reader(["fr"], gpu=True)
        self._crop_window()

    def _crop_window(self):
        height, width = self.image.shape[:2]

        # Crop hunt panel and current coordinates
        crop_height = height // 2
        crop_width = (width // 8) + 50
        self.cropped_hunt_panel = self.image[0:crop_height, 0:crop_width]
        self.cropped_coords = self.image[70:95, 0:90]

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(debug_dir, "cropped_hunt_panel.png"), self.cropped_hunt_panel)
            cv2.imwrite(os.path.join(debug_dir, "cropped_coords.png"), self.cropped_coords)

    def get_coordinates(self) -> Coordinates:
        easyocr_coords = self.reader.readtext(
            self.cropped_coords,
            contrast_ths=0.1,  # Lower this to detect more low-contrast characters
            text_threshold=0.5,  # Lower to be more lenient with character detection
            low_text=0.2,  # Lower to better detect small characters like minus signs
            width_ths=1.2,  # Slightly increase to better group characters
            add_margin=0.1,  # Add some margin around the text
            paragraph=False,  # Ensure characters aren't incorrectly grouped
        )

        for detection in easyocr_coords:
            self.logger.debug(
                f"Detected coordinates: '{detection[1]}' (confidence: {detection[2]:.2f})"
            )

        return Coordinates(easyocr_coords)

    def get_hint(self) -> str:
        easyocr_hints = self.reader.readtext(
            self.cropped_hunt_panel,
            contrast_ths=0.2,
            text_threshold=0.6,
            low_text=0.3,
            width_ths=0.5,
        )

        hint = None
        for i, ocr_result in enumerate(easyocr_hints):
            detection = Detection(ocr_result).sanitize()
            self.logger.debug(f"OCR detected text: {detection}")

            # We use the "EN COURS" tag to identify which text is a hint in the image
            if detection.text == "EN COURS":
                hint = Hint(easyocr_hints[i - 1][1])
                self.hint_box = easyocr_hints[i - 1][0]
            elif "EN COURS" in detection.text:
                # replace EN COURS in case it is included in the captured text
                hint = Hint(detection.text.replace("EN COURS", ""))
                self.hint_box = detection.box

        return hint

    def get_arrow_direction(self):
        hint_top_left = self.hint_box[0]
        hint_bot_left = self.hint_box[3]
        arrow_crop = self.image[
            hint_top_left[1] - 20 : hint_bot_left[1] + 20, 10 : hint_top_left[0]
        ]

        # Create debug directory if it doesn't exist
        if self.logger.getEffectiveLevel() == logging.DEBUG:
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(debug_dir, "arrow_crop.png"), arrow_crop)

        # The part below was fully written by Claude Sonnet 3.7
        # Convert the image to grayscale
        gray = cv2.cvtColor(arrow_crop, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detector
        edges = cv2.Canny(gray, 50, 150)

        # Find contours in the image
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Find the largest contour (assuming it's the arrow)
        if not contours:
            self.logger.warning("No contours found in arrow detection")
            return None

        arrow_contour = max(contours, key=cv2.contourArea)

        # Get the minimum area rectangle that bounds the arrow
        rect = cv2.minAreaRect(arrow_contour)
        box = cv2.boxPoints(rect)
        box = np.intp(box)

        # Get the moments of the contour to find the centroid
        M = cv2.moments(arrow_contour)
        if M["m00"] == 0:
            self.logger.warning("Could not compute moments for arrow contour")
            return None

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        # Analyze the contour to detect the arrow head
        # We'll use the distance from centroid to contour points
        # The farthest point is likely to be one of the arrow extremities
        max_dist = 0
        farthest_point = None

        for point in arrow_contour:
            point = point[0]
            dist = math.sqrt((point[0] - cx) ** 2 + (point[1] - cy) ** 2)
            if dist > max_dist:
                max_dist = dist
                farthest_point = point

        # Find another key point - the second farthest point from the centroid
        # that is far from the first farthest point
        min_distance_between_extremities = max_dist * 0.7  # Threshold
        second_max_dist = 0
        second_farthest_point = None

        for point in arrow_contour:
            point = point[0]
            dist_to_centroid = math.sqrt((point[0] - cx) ** 2 + (point[1] - cy) ** 2)
            if farthest_point is not None:
                dist_to_farthest = math.sqrt(
                    (point[0] - farthest_point[0]) ** 2 + (point[1] - farthest_point[1]) ** 2
                )
                if (
                    dist_to_centroid > second_max_dist
                    and dist_to_farthest > min_distance_between_extremities
                ):
                    second_max_dist = dist_to_centroid
                    second_farthest_point = point

        # Determine which point is the arrow head
        # This is a simplified approach - the arrow head is likely the point
        # that has fewer neighbors around it in the contour
        arrow_head = None
        arrow_tail = None

        if farthest_point is not None and second_farthest_point is not None:
            # Calculate the approximate area near both extremity points
            radius = max_dist * 0.2  # Define a radius for neighborhood
            head_neighbors = 0
            tail_neighbors = 0

            for point in arrow_contour:
                point = point[0]
                dist_to_farthest = math.sqrt(
                    (point[0] - farthest_point[0]) ** 2 + (point[1] - farthest_point[1]) ** 2
                )
                dist_to_second = math.sqrt(
                    (point[0] - second_farthest_point[0]) ** 2
                    + (point[1] - second_farthest_point[1]) ** 2
                )

                if dist_to_farthest < radius:
                    head_neighbors += 1
                if dist_to_second < radius:
                    tail_neighbors += 1

            # The arrow head typically has fewer neighbors (more pointed)
            if head_neighbors < tail_neighbors:
                arrow_head = farthest_point
                arrow_tail = second_farthest_point
            else:
                arrow_head = second_farthest_point
                arrow_tail = farthest_point

        # Draw arrow direction
        if arrow_head is not None and arrow_tail is not None:
            # Calculate the direction
            dx = arrow_head[0] - arrow_tail[0]
            dy = arrow_head[1] - arrow_tail[1]

            # Calculate angle in degrees
            angle = math.atan2(dy, dx) * 180 / math.pi

            # Determine the cardinal direction
            if -45 <= angle < 45:
                direction = "RIGHT"
                self.logger.info("Arrow direction identified: RIGHT")
            elif 45 <= angle < 135:
                direction = "DOWN"
                self.logger.info("Arrow direction identified: DOWN")
            elif -135 <= angle < -45:
                direction = "UP"
                self.logger.info("Arrow direction identified: UP")
            else:
                direction = "LEFT"
                self.logger.info("Arrow direction identified: LEFT")

        # Save or display the results

        if arrow_head is not None and arrow_tail is not None:
            return direction
        else:
            self.logger.warning("Could not determine arrow direction")
            return None
