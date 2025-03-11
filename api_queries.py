import logging
import os

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

    request = f"https://{host}/treasure-hunt?x={current_coords[0].strip()}&y={current_coords[1].strip()}&direction={direction}&$limit=50&lang=fr"
    logger.info(f"Sending API request: {request}")
    print(f"Sent request {request}")

    try:
        response = requests.get(request, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
        logger.info(
            f"API request successful, received {len(response.json()['data'])} POI data points"
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        print(f"An error occurred: {e}")
        return None


def parse_response_to_dict(response):
    logger.info("Parsing API response to dictionary")
    distances = {}
    partial_matches = {}  # New dictionary to handle partial matches

    if not response or "data" not in response:
        logger.warning("Empty or invalid API response")
        return {}, {}

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

    logger.info(f"Parsed {len(distances)} POIs with distances")
    logger.info("Parsed distances dictionary:")
    logger.info(distances)
    logger.info("Parsed partial matches dictionary:")
    logger.info(partial_matches)
    return distances, partial_matches


def find_distance(hint, distances, partial_matches):
    logger.info(f"Searching for distance for hint: '{hint}'")

    # First check for exact match
    if hint in distances:
        logger.info(f"Found exact match for '{hint}' with distance {distances[hint]}")
        return distances[hint]

    # Then check for partial match
    if hint in partial_matches:
        full_name = partial_matches[hint]
        logger.info(
            f"Found partial match for '{hint}' -> '{full_name}' with distance {distances[full_name]}"
        )
        return distances[full_name]

    # If still no match, try removing accents from hint
    hint_no_accents = remove_accents(hint)
    if hint_no_accents in partial_matches:
        full_name = partial_matches[hint_no_accents]
        logger.info(
            f"Found match after accent removal: '{hint}' -> '{full_name}' with distance {distances[full_name]}"
        )
        return distances[full_name]

    logger.warning(f"No distance found for hint '{hint}'")
    print(f"{hint} not found in")
    print(distances.keys())
    return None
