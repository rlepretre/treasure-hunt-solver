import logging
import math
import os
import re
import time
from datetime import datetime

import cv2
import easyocr
import numpy as np

from utils import remove_accents

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("computer_vision")


def extract_coordinates(ocr_result):
    coordinates = ocr_result[1][1].replace("~", "-").replace(" ", "")

    pattern = r"^-?\d{1,2},-?\d{1,2}$"

    # Example usage:
    if re.match(pattern, coordinates):
        logger.info(f"Valid coordinates format: {coordinates}")
        print("Valid format: ")
        print(coordinates.split(","))
        return coordinates.split(",")
    else:
        logger.warning(
            f"Invalid coordinates format: {ocr_result[1][1]}, {ocr_result[2][1]}"
        )
        print("Invalid format")
        print(
            (
                ocr_result[1][1].replace(",", "").strip(),
                ocr_result[2][1].replace(",", "").strip(),
            )
        )
        return (
            ocr_result[1][1].replace(",", "").strip(),
            ocr_result[2][1].replace(",", "").strip(),
        )


def read_image_text(image):
    # Read and crop the image
    height, width = image.shape[:2]

    # Crop top left 16th
    crop_height = height // 2
    crop_width = (width // 8) + 50
    cropped_image = image[0:crop_height, 0:crop_width]

    # Create debug directory if it doesn't exist
    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
    os.makedirs(debug_dir, exist_ok=True)

    cv2.imwrite(os.path.join(debug_dir, "cropped_image.png"), cropped_image)

    # Initialize OCR engine
    logger.info("Initializing OCR engine")
    reader = easyocr.Reader(["fr"], gpu=True)

    # Time EasyOCR on cropped image
    logger.info("Starting OCR text recognition")
    start_time = time.time()
    easyocr_result = reader.readtext(cropped_image)
    end_time = time.time()
    logger.info(f"OCR completed in {end_time - start_time:.2f} seconds")

    # Log all detected text
    for idx, (bbox, text, conf) in enumerate(easyocr_result):
        logger.info(f"OCR detected text #{idx}: '{text}' (confidence: {conf:.2f})")

    coordinates = extract_coordinates(easyocr_result)
    logger.info(f"Extracted coordinates: {coordinates}")

    hint = None
    hint_box = None
    for i, detection in enumerate(easyocr_result):
        if "EN COUR" in detection[1]:
            hint = easyocr_result[i - 1][1]
            hint_box = easyocr_result[i - 1][0]
            logger.info(f"Detected hint: '{hint}'")

    hint = remove_accents(hint.replace("œ", "oe").replace("'", ""))
    return cropped_image, coordinates, hint, hint_box


def identify_arrow_direction(image, hint_box):
    logger.info("Identifying arrow direction")
    hint_top_left = hint_box[0]
    hint_bot_left = hint_box[3]
    arrow_crop = image[
        hint_top_left[1] - 2 : hint_bot_left[1] + 20, 10 : hint_top_left[0]
    ]

    # Create debug directory if it doesn't exist
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
        logger.warning("No contours found in arrow detection")
        print("No contours found.")
        return None

    arrow_contour = max(contours, key=cv2.contourArea)

    # Get the minimum area rectangle that bounds the arrow
    rect = cv2.minAreaRect(arrow_contour)
    box = cv2.boxPoints(rect)
    box = np.intp(box)

    # Get the moments of the contour to find the centroid
    M = cv2.moments(arrow_contour)
    if M["m00"] == 0:
        logger.warning("Could not compute moments for arrow contour")
        print("Could not compute moments.")
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
                (point[0] - farthest_point[0]) ** 2
                + (point[1] - farthest_point[1]) ** 2
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
                (point[0] - farthest_point[0]) ** 2
                + (point[1] - farthest_point[1]) ** 2
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
            direction = 0  # right
            logger.info("Arrow direction identified: RIGHT")
        elif 45 <= angle < 135:
            direction = 2  # down
            logger.info("Arrow direction identified: DOWN")
        elif -135 <= angle < -45:
            direction = 6  # up
            logger.info("Arrow direction identified: UP")
        else:
            direction = 4  # left
            logger.info("Arrow direction identified: LEFT")

    # Save or display the results

    if arrow_head is not None and arrow_tail is not None:
        return direction
    else:
        logger.warning("Could not determine arrow direction")
        return None
