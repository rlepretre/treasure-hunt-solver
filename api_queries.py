import json
import logging
import os
import re

import requests
from dotenv import load_dotenv

from utils import remove_accents

logger = logging.getLogger("api_queries")
load_dotenv()
host = os.getenv("HOST")
token = os.getenv("TOKEN")
origin = os.getenv("ORIGIN")


def send_dofusdb_request(current_coords, direction):
    headers = {
        "Host": host,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "token": token,
        "Origin": origin,
        "Connection": "keep-alive",
        "Referer": origin,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=0",
        "TE": "trailers",
    }

    pattern = r"^-?\d{1,2}$"

    # Example usage:
    if re.match(pattern, current_coords[0]) and re.match(pattern, current_coords[1]):
        request = f"https://{host}/treasure-hunt?x={current_coords[0].strip()}&y={current_coords[1].strip()}&direction={direction}&$limit=50&lang=fr"

        try:
            response = requests.get(request, headers=headers)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None


def parse_response_to_dict(response):
    logger.info("Parsing API response to dictionary")
    distances = {}
    partial_matches = {}  # New dictionary to handle partial matches

    if not response or "data" not in response:
        logger.warning("Empty or invalid API response")
        return {}, {}
    # Save the response as JSON in debug directory
    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
    os.makedirs(debug_dir, exist_ok=True)
    with open(os.path.join(debug_dir, "response.json"), "w") as response_file:
        json.dump(response, response_file, indent=4)

    for obj in response["data"]:
        for poi in obj["pois"]:
            name = poi["name"]["fr"]
            distance = obj["distance"]

            if name in distances.keys():
                if (
                    distances[remove_accents(name.replace("œ", "oe").replace("'", ""))]
                    < distance
                ):
                    distance = distances[name]

            # Store the full name as key with its distance
            distances[name] = distance

            distances[remove_accents(name.replace("œ", "oe").replace("'", ""))] = (
                distance
            )

            # Generate partial keys for matching
            words = name.split()
            for i in range(1, len(words) + 1):
                for j in range(len(words) - i + 1):
                    partial_key = " ".join(words[j : j + i])
                    partial_matches[partial_key] = name  # Map partial key to full name

                    # Also store non-accented version
                    partial_matches[remove_accents(partial_key)] = name

    logger.info("Parsed distances dictionary:")
    for hint in distances:
        logger.info(f"{hint}: {distances[hint]}")
    return distances, partial_matches


def find_distance(hint, distances, partial_matches):
    logger.info(f"Searching for distance for hint: '{hint}'")

    # First check for exact match
    if hint in distances:
        return distances[hint]

    # Then check for partial match
    if hint in partial_matches:
        full_name = partial_matches[hint]
        return distances[full_name]

    # If still no match, try removing accents from hint
    hint_no_accents = remove_accents(hint)
    if hint_no_accents in partial_matches:
        full_name = partial_matches[hint_no_accents]
        # logger.info(
        #     f"Found match after accent removal: '{hint}' -> '{full_name}' with distance {distances[full_name]}"
        # )
        return distances[full_name]

    logger.warning(f"No distance found for hint '{hint}'")

    return None
