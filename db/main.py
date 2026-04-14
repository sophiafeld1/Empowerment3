import sqlite3
from pathlib import Path


class E3Database:
    """Encapsulates schema creation and inspection for E3 sponsor data."""

    TABLE_NAME = "possible_sponsors"

    # Full target schema (order = column order in new table).
    SCHEMA = [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT NOT NULL"),
        ("industry", "TEXT"),
        ("description", "TEXT"),
        ("goods_and_services", "TEXT"),
        ("services_to_E3", "TEXT"),
        ("E3_provides", "TEXT"),
        ("email", "TEXT"),
        ("phone", "TEXT"),
        ("contact_info", "TEXT"),
        ("website", "TEXT"),
        ("city", "TEXT"),
        ("state", "TEXT"),
        ("zip", "INTEGER"),
        ("physical_location", "INTEGER"),
        ("geographical_priorities", "TEXT"),
        ("company_size", "TEXT"),
        ("giving_priorities", "TEXT"),
        ("jmu_affiliated", "INTEGER"),
        ("past_e3_engagement", "TEXT"),
    ]

    # Removed from schema; triggers rebuild + data mapping from serves_populations -> giving_priorities.
    OBSOLETE_COLUMNS = frozenset(
        {
            "has_physical_location",
            "location_accessibility_level",
            "has_community_giving_program",
            "serves_populations",
            "collaborates_with_community",
        }
    )

    def __init__(self):
        self.db_path = Path(__file__).resolve().parent / "E3_database.db"

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _expected_column_names(self):
        return [name for name, _ in self.SCHEMA]

    def _rebuild_table(self, cursor):
        cursor.execute(f"SELECT * FROM {self.TABLE_NAME}")
        rows = cursor.fetchall()
        cursor.execute(f"PRAGMA table_info({self.TABLE_NAME})")
        old_cols = [row[1] for row in cursor.fetchall()]

        def row_dict(row):
            return {old_cols[i]: row[i] for i in range(len(old_cols))}

        new_table = f"{self.TABLE_NAME}_new"
        cols_sql = ", ".join(f"{name} {definition}" for name, definition in self.SCHEMA)
        cursor.execute(f"DROP TABLE IF EXISTS {new_table}")
        cursor.execute(f"CREATE TABLE {new_table} ({cols_sql})")

        col_names = [name for name, _ in self.SCHEMA]
        placeholders = ", ".join(["?"] * len(col_names))
        insert_sql = f"INSERT INTO {new_table} ({', '.join(col_names)}) VALUES ({placeholders})"

        for row in rows:
            d = row_dict(row)
            values = []
            for col_name, _ in self.SCHEMA:
                if col_name == "goods_and_services":
                    values.append(None)
                elif col_name == "contact_info":
                    values.append(None)
                elif col_name == "physical_location":
                    old_val = d.get("physical_location")
                    if old_val in (1, "1", True):
                        values.append(1)
                    elif old_val in (0, "0", False):
                        values.append(0)
                    else:
                        values.append(None)
                elif col_name == "geographical_priorities":
                    values.append(None)
                elif col_name == "giving_priorities":
                    values.append(d.get("serves_populations"))
                else:
                    values.append(d.get(col_name))
            cursor.execute(insert_sql, tuple(values))

        cursor.execute(f"DROP TABLE {self.TABLE_NAME}")
        cursor.execute(f"ALTER TABLE {new_table} RENAME TO {self.TABLE_NAME}")

    def create_or_update_schema(self):
        """Create table if missing, migrate off obsolete columns, add any new columns."""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (self.TABLE_NAME,),
        )
        if not cursor.fetchone():
            cols_sql = ", ".join(
                f"{name} {definition}" for name, definition in self.SCHEMA
            )
            cursor.execute(f"CREATE TABLE {self.TABLE_NAME} ({cols_sql})")
            conn.commit()
            conn.close()
            return

        cursor.execute(f"PRAGMA table_info({self.TABLE_NAME})")
        table_info = cursor.fetchall()
        existing = {row[1] for row in table_info}
        expected = {name for name, _ in self.SCHEMA}
        type_map = {row[1]: row[2].upper() for row in table_info}
        needs_type_rebuild = type_map.get("physical_location") != "INTEGER"

        if existing & self.OBSOLETE_COLUMNS or (expected - existing) or needs_type_rebuild:
            self._rebuild_table(cursor)

        cursor.execute(f"PRAGMA table_info({self.TABLE_NAME})")
        existing = {row[1] for row in cursor.fetchall()}
        for column_name, column_def in self.SCHEMA:
            if column_name not in existing:
                cursor.execute(
                    f"ALTER TABLE {self.TABLE_NAME} ADD COLUMN {column_name} {column_def}"
                )

        conn.commit()
        conn.close()

    def display_all_data(self):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {self.TABLE_NAME}")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            print(row)


if __name__ == "__main__":
    db = E3Database()
    db.create_or_update_schema()
    print("Database schema is ready:\n")
    db.display_all_data()
