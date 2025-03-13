import logging
import os

import cv2
import easyocr

from detection import Detection


class ImageReader:
    def __init__(self, image):
        self.image = image
        self.logger = logging.getLogger("image_reader")

    def extract_text(self):
        height, width = self.image.shape[:2]

        # Crop hunt panel and current coordinates
        crop_height = height // 2
        crop_width = (width // 8) + 50
        cropped_hunt_panel = self.image[0:crop_height, 0:crop_width]
        cropped_coords = self.image[70:95, 0:90]

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(debug_dir, "cropped_hunt_panel.png"), cropped_hunt_panel)
            cv2.imwrite(os.path.join(debug_dir, "cropped_coords.png"), cropped_coords)

        reader = easyocr.Reader(["fr"], gpu=True)
        easyocr_hints = reader.readtext(
            cropped_hunt_panel,
            contrast_ths=0.2,
            text_threshold=0.6,
            low_text=0.3,
            width_ths=0.5,
        )
        easyocr_coords = reader.readtext(
            cropped_coords,
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

        # coordinates = extract_coordinates(easyocr_coords)
        # self.logger.info(f"Extracted coordinates: {coordinates}")

        hint = None
        hint_box = None
        for i, ocr_result in enumerate(easyocr_hints):
            detection = Detection(ocr_result).sanitize()
            self.logger.debug(f"OCR detected text: {detection}")
            if detection.text == "EN COURS":
                hint = easyocr_hints[i - 1][1]
                hint_box = easyocr_hints[i - 1][0]
            elif "EN COURS" in detection.text:
                # replace EN COURS in case it is include in captured text
                hint = detection.text.replace("EN COURS", "")
                hint_box = detection.box

        return cropped_image, coordinates, hint, hint_box
