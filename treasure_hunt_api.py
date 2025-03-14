import json
import logging
import os

import requests
from dotenv import load_dotenv

from models import Hint

load_dotenv()


class TreasureHuntAPI:
    def __init__(self):
        self.logger = logging.getLogger("api_queries")
        self.host = os.getenv("HOST")
        self.token = os.getenv("TOKEN")
        self.origin = os.getenv("ORIGIN")
        self.headers = {
            "Host": self.host,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "token": self.token,
            "Origin": self.origin,
            "Connection": "keep-alive",
            "Referer": self.origin,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Priority": "u=0",
            "TE": "trailers",
        }

    def send_request(self, current_coords, direction):
        if current_coords.are_valid():
            request = f"https://{self.host}/treasure-hunt?x={current_coords.x}&y={current_coords.y}&direction={direction}&$limit=50&lang=fr"
        else:
            self.logger.warning(f"Invalid coordinates {current_coords}")
            return None

        try:
            response = requests.get(request, headers=self.headers)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None

    def parse_response_to_dict(self, response):
        self.logger.info("Parsing API response to dictionary")
        distances = {}
        partial_matches = {}  # New dictionary to handle partial matches

        if not response or "data" not in response:
            self.logger.warning("Empty or invalid API response")
            return {}, {}
        # Save the response as JSON in debug directory
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            with open(os.path.join(debug_dir, "response.json"), "w") as response_file:
                json.dump(response, response_file, indent=4)

        for obj in response["data"]:
            for poi in obj["pois"]:
                hint = Hint(poi["name"]["fr"]).sanitize()
                distance = obj["distance"]

                if hint.text in distances.keys():
                    if distances[hint.text] < distance:
                        distance = distances[hint.text]

                # Store the full name as key with its distance
                distances[hint.text] = distance

                # Generate partial keys for matching
                words = hint.text.split()
                for i in range(1, len(words) + 1):
                    for j in range(len(words) - i + 1):
                        partial_key = " ".join(words[j : j + i])
                        partial_matches[partial_key] = hint.text  # Map partial key to full name

        self.logger.info("Parsed distances dictionary:")
        for hint in distances:
            self.logger.info(f"{hint}: {distances[hint]}")
        return distances, partial_matches

    def find_distance(self, hint, distances, partial_matches):
        self.logger.info(f"Searching for distance for hint: '{hint}'")

        # First check for exact match
        if hint in distances:
            return distances[hint]

        # Then check for partial match
        if hint in partial_matches:
            full_name = partial_matches[hint]
            return distances[full_name]

        self.logger.warning(f"No distance found for hint '{hint}'")

        return None
