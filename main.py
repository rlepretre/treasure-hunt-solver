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

log_file = os.path.join(
    log_dir, f"treasure_hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("main")


def process_image():
    try:
        logger.info("Starting treasure hunt image processing")
        start = time.process_time()
        window = WindowInformationExtractor("Ina")
        image = window.capture_window()
        # Create debug directory if it doesn't exist
        os.makedirs("debug", exist_ok=True)

        logger.info("Reading text from image")
        cropped_image, current_coords, hint, hint_box = read_image_text(image)
        logger.info(f"Current coordinates: {current_coords}, Hint: {hint}")

        direction = identify_arrow_direction(cropped_image, hint_box)

        logger.info(
            f"Sending API request with coords: {current_coords}, direction: {direction}"
        )
        response = send_dofusdb_request(current_coords, direction)
        distances, partial_matches = parse_response_to_dict(response)
        # Find the first key that contains the hint string

        logger.info(f"Finding distance for hint: '{hint}'")
        hint_distance = find_distance(hint, distances, partial_matches)
        if hint_distance is None:
            logger.warning("No distance found, trying with negative x coordinate")
            current_coords = ["-" + current_coords[0], current_coords[1]]
            logger.info(f"Retrying with coordinates: {current_coords}")
            response = send_dofusdb_request(current_coords, direction)
            distances, partial_matches = parse_response_to_dict(response)
            hint_distance = find_distance(hint, distances, partial_matches)

        if hint_distance is None:
            logger.warning("No distance found, trying with negative y coordinate")
            current_coords = [current_coords[0][1:], "-" + current_coords[1]]
            logger.info(f"Retrying with coordinates: {current_coords}")
            response = send_dofusdb_request(current_coords, direction)
            distances, partial_matches = parse_response_to_dict(response)
            hint_distance = find_distance(hint, distances, partial_matches)

        if hint_distance is None:
            logger.warning("No distance found, trying with negative y coordinate")
            current_coords = ["-" + current_coords[0], current_coords[1]]
            logger.info(f"Retrying with coordinates: {current_coords}")
            response = send_dofusdb_request(current_coords, direction)
            distances, partial_matches = parse_response_to_dict(response)
            hint_distance = find_distance(hint, distances, partial_matches)

        target_coords = current_coords.copy()
        logger.info(f"Hint distance: {hint_distance}")
        print(hint_distance)

        if direction == 0:  # right
            target_coords[0] = int(target_coords[0]) + int(hint_distance)
            logger.info(f"Moving RIGHT by {hint_distance}")
        elif direction == 2:  # down
            target_coords[1] = int(target_coords[1]) + int(hint_distance)
            logger.info(f"Moving DOWN by {hint_distance}")
        elif direction == 4:  # left
            target_coords[0] = int(target_coords[0]) - int(hint_distance)
            logger.info(f"Moving LEFT by {hint_distance}")
        elif direction == 6:  # up
            target_coords[1] = int(target_coords[1]) - int(hint_distance)
            logger.info(f"Moving UP by {hint_distance}")

        logger.info(f"Target coordinates: {target_coords}")
        print(f"/travel {target_coords[0]} {target_coords[1]}")
        pyperclip.copy(f"/travel {target_coords[0]} {target_coords[1]}")
        winsound.PlaySound("assets/notif.wav", winsound.SND_FILENAME)
        process_time = time.process_time() - start
        logger.info(f"Processing completed in {process_time:.2f} seconds")
        print(process_time)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"An error occurred: {e}")


def main():
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
