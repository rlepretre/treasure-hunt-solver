import argparse
import logging
import os
import time
import winsound
from datetime import datetime

import keyboard
import pyperclip

from api_queries import find_distance, parse_response_to_dict, send_dofusdb_request
from computer_vision import identify_arrow_direction, read_image_text
from window_extractor import WindowInformationExtractor

# Setup logging for main application
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f"treasure_hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("main")


def process_image():
    try:
        start = time.process_time()
        window = WindowInformationExtractor("Ina")
        image = window.capture_window()
        # Create debug directory if it doesn't exist
        os.makedirs("debug", exist_ok=True)

        cropped_image, current_coords, hint, hint_box = read_image_text(image)
        logger.info(f"Current coordinates: {current_coords}, Hint: {hint}")

        direction = identify_arrow_direction(cropped_image, hint_box)

        response = send_dofusdb_request(current_coords, direction)
        distances, partial_matches = parse_response_to_dict(response)
        # Find the first key that contains the hint string

        hint_distance = find_distance(hint, distances, partial_matches)

        target_coords = current_coords.copy()
        print(hint_distance)

        if direction == 0:  # right
            target_coords[0] = int(target_coords[0]) + int(hint_distance)
        elif direction == 2:  # down
            target_coords[1] = int(target_coords[1]) + int(hint_distance)
        elif direction == 4:  # left
            target_coords[0] = int(target_coords[0]) - int(hint_distance)
        elif direction == 6:  # up
            target_coords[1] = int(target_coords[1]) - int(hint_distance)

        pyperclip.copy(f"/travel {target_coords[0]} {target_coords[1]}")
        winsound.PlaySound("assets/notif.wav", winsound.SND_FILENAME)
        process_time = time.process_time() - start
        logger.info(f"Processing completed in {process_time:.2f} seconds")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"An error occurred: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_dir", default="debug_output", help="Directory for debug images")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    logger.info("Starting treasure hunt solver application")
    print("Program running. Press Ctrl+D to process image, or Ctrl+C to exit.")
    keyboard.add_hotkey("ctrl+d", lambda: process_image())

    try:
        keyboard.wait("ctrl+c")  # Keep the program running until Ctrl+C is pressed
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
        print("\nProgram terminated.")


if __name__ == "__main__":
    main()
