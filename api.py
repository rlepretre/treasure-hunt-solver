import json
import logging
import sqlite3

import pandas as pd

from models import Coordinates, Hint


class API:
    def __init__(self):
        self.logger = logging.getLogger("api")
        self.conn = sqlite3.connect("data/treasure_hunt.db")

    def find_distance(self, hint, current_coords, direction):
        items = self.get_hints(current_coords, direction)

        return items

    def get_hint_coordinates(self, current_coords, direction, hint):
        query = ""
        params = (0, 0, 0)
        if direction == "RIGHT":
            query = """
                SELECT name_fr, x, y
                FROM hints_coordinates
                WHERE y = ?
                AND x BETWEEN ? AND ?
                ORDER BY x ASC
            """
            params = (current_coords.y, current_coords.x, int(current_coords.x) + 10)

        elif direction == "DOWN":
            query = """
                SELECT name_fr, x, y
                FROM hints_coordinates
                WHERE x = ?
                AND y BETWEEN ? AND ?
                ORDER BY y ASC
            """
            params = (current_coords.x, current_coords.y, int(current_coords.y) + 10)

        elif direction == "LEFT":
            query = """
                SELECT name_fr, x, y
                FROM hints_coordinates
                WHERE y = ?
                AND x BETWEEN ? AND ?
                ORDER BY x ASC
            """
            params = (current_coords.y, int(current_coords.x) - 10, current_coords.x)

        elif direction == "UP":
            query = """
                SELECT name_fr, x, y
                FROM hints_coordinates
                WHERE x = ?
                AND y BETWEEN ? AND ?
                ORDER BY y ASC
            """
            params = (current_coords.x, int(current_coords.y) - 10, current_coords.y)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        items = cursor.fetchall()
        hint_coords = {}
        hint_partial_match_coords = {}
        for item in items:
            key_hint = Hint(item[0]).sanitize()
            coords = Coordinates(x=item[1], y=item[2])
            if coords != current_coords:
                if key_hint.text in hint_coords.keys():
                    self.logger.debug(
                        f"Check if {key_hint} ,{coords} at {coords.get_distance(current_coords)} is less than {hint_coords[key_hint.text]}{hint_coords[key_hint.text].get_distance(current_coords)}"
                    )
                    if coords.get_distance(current_coords) < hint_coords[
                        key_hint.text
                    ].get_distance(current_coords):
                        hint_coords[key_hint.text] = coords
                    else:
                        coords = hint_coords[key_hint.text]
                else:
                    hint_coords[key_hint.text] = coords
                words = key_hint.text.split()
                for i in range(1, len(words) + 1):
                    for j in range(len(words) - i + 1):
                        partial_key = " ".join(words[j : j + i])
                        hint_partial_match_coords[partial_key] = coords
        target_coords = hint_coords.get(hint.text)
        if not target_coords:
            self.logger.info(f"Hint {hint} not found, partial match")
            target_coords = hint_partial_match_coords.get(hint.text)
        return target_coords

    def build_db(self):
        print("Building database...")
        self.logger.info("Building database...")
        hint_and_maps = json.load(open("data/clues_full.json"))
        hints_df = pd.DataFrame(hint_and_maps["clues"])
        hints_df = hints_df.rename(columns={"clue-id": "hint-id"})
        hints_df.columns = hints_df.columns.str.replace("-", "_")

        maps = hint_and_maps["maps"]

        hint_ids = []
        x_coords = []
        y_coords = []

        for _, details in maps.items():
            position = details.get("position", {})
            x = position.get("x", 0)
            y = position.get("y", 0)
            clues = details.get("clues", [])

            for clue in clues:
                hint_ids.append(clue)
                x_coords.append(x)
                y_coords.append(y)

        maps_df = pd.DataFrame({"hint_id": hint_ids, "x": x_coords, "y": y_coords})
        maps_df = maps_df.drop_duplicates()
        hints_coordinates = hints_df.merge(maps_df, on="hint_id")
        hints_coordinates.to_sql("hints_coordinates", self.conn, if_exists="replace", index=False)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS hints_coordinates_hint_id_x_y_index
            ON hints_coordinates (name_fr, x, y)
        """)

        self.logger.info("Database built successfully")

    def table_to_df(self, table_name):
        return pd.read_sql(f"SELECT * FROM {table_name}", self.conn)
