import sqlite3
from pathlib import Path


class E3Database:
    """Encapsulates schema creation and inspection for E3 sponsor data."""

    TABLE_NAME = "possible_sponsors"
    SCHEMA = [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT NOT NULL"),
        ("industry", "TEXT"),
        ("description", "TEXT"),
        ("services_to_E3", "TEXT"),
        ("E3_provides", "TEXT"),
        ("email", "TEXT"),
        ("phone", "TEXT"),
        ("city", "TEXT"),
        ("state", "TEXT"),
        ("zip", "INTEGER"),
        ("website", "TEXT"),
        ("company_size", "TEXT"),
        ("has_physical_location", "INTEGER"),
        ("location_accessibility_level", "TEXT"),
        ("has_community_giving_program", "INTEGER"),
        ("serves_populations", "TEXT"),
        ("jmu_affiliated", "INTEGER"),
        ("past_e3_engagement", "TEXT"),
        ("collaborates_with_community", "TEXT"),
    ]

    def __init__(self):
        self.db_path = Path(__file__).resolve().parent / "E3_database.db"

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def create_or_update_schema(self):
        """Create table if missing, then add any missing columns."""
        conn = self._connect()
        cursor = conn.cursor()

        base_columns_sql = ", ".join(
            f"{name} {definition}" for name, definition in self.SCHEMA[:12]
        )
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} ({base_columns_sql})"
        )

        cursor.execute(f"PRAGMA table_info({self.TABLE_NAME})")
        existing_columns = {row[1] for row in cursor.fetchall()}

        for column_name, column_def in self.SCHEMA:
            if column_name not in existing_columns:
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