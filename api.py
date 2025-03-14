import json
import logging
import os
import sqlite3

import pandas as pd


class API:
    def __init__(self):
        self.logger = logging.getLogger("api")
        self.conn = sqlite3.connect("data/treasure_hunt.db")
        if not os.path.exists("data/treasure_hunt.db"):
            self._build_db()

    def find_distance(self, hint, current_coords, direction):
        items = self.get_hints(current_coords, direction)

        return items

    def get_hints(self, current_coords, direction):
        if direction == "RIGHT":
            query = """
                SELECT h.hint_id, hc.x, hc.y
                FROM hints_coordinates hc
                INNER JOIN hints h ON h.hint_id = hc.hint_id
                WHERE hc.y = ? 
                AND hc.x BETWEEN ? AND ?
                ORDER BY hc.x ASC
            """
            params = (current_coords["y"], current_coords["x"], current_coords["x"] + 10)

        elif direction == "DOWN":
            query = """
                SELECT h.hint_id, hc.x, hc.y
                FROM hints_coordinates hc
                INNER JOIN hints h ON h.hint_id = hc.hint_id
                WHERE hc.x = ? 
                AND hc.y BETWEEN ? AND ?
                ORDER BY hc.y ASC
            """
            params = (current_coords["x"], current_coords["y"], current_coords["y"] + 10)

        elif direction == "LEFT":
            query = """
                SELECT h.hint_id, hc.x, hc.y
                FROM hints_coordinates hc
                INNER JOIN hints h ON h.hint_id = hc.hint_id
                WHERE hc.y = ? 
                AND hc.x BETWEEN ? AND ?
                ORDER BY hc.x DESC
            """
            params = (current_coords["y"], current_coords["x"] - 10, current_coords["x"])

        elif direction == "UP":
            query = """
                SELECT h.hint_id, hc.x, hc.y
                FROM hints_coordinates hc
                INNER JOIN hints h ON h.hint_id = hc.hint_id
                WHERE hc.x = ? 
                AND hc.y BETWEEN ? AND ?
                ORDER BY hc.y DESC
            """
            params = (current_coords["x"], current_coords["y"] - 10, current_coords["y"])

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        items = cursor.fetchall()
        return items

    def _build_db(self):
        self.logger.info("Building database...")
        hint_and_maps = json.load(open("data/clues_full.json"))
        hints = pd.DataFrame(hint_and_maps["clues"])
        hints.rename(columns={"clue_id": "hint_id"}, inplace=True)
        hints.columns = hints.columns.str.replace("-", "_")

        hints.to_sql("hints", self.conn, if_exists="replace", index=False)

        maps = hint_and_maps["maps"]

        hint_ids = []
        x_coords = []
        y_coords = []

        for hint_id, details in maps.items():
            position = details.get("position", {})
            x = position.get("x", 0)
            y = position.get("y", 0)
            clues = details.get("clues", [])

            for clue in clues:
                hint_ids.append(clue)
                x_coords.append(x)
                y_coords.append(y)

        maps_df = pd.DataFrame({"hint_id": hint_ids, "x": x_coords, "y": y_coords})

        maps_df.to_sql("hints_coordinates", self.conn, if_exists="replace", index=False)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS hints_coordinates_hint_id_x_y_index 
            ON hints_coordinates (hint_id, x, y)
        """)

        self.logger.info("Database built successfully")
