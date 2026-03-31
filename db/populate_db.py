import csv
import sqlite3
from pathlib import Path


def populate_E3_database():
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir.parent / "data" / "E3_Database_2026.csv"
    db_path = base_dir / "E3_database.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    inserted = 0
    skipped_blank = 0
    skipped_duplicate = 0

    cursor.execute("SELECT name FROM possible_sponsors WHERE name IS NOT NULL")
    existing_names = {row[0].strip().lower() for row in cursor.fetchall() if row[0].strip()}

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = (row.get("Name") or "").strip()
            if not name:
                skipped_blank += 1
                continue

            normalized_name = name.lower()
            if normalized_name in existing_names:
                skipped_duplicate += 1
                continue

            cursor.execute(
                """
                INSERT INTO possible_sponsors (name, industry, description, email, phone, website)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    row.get("Industry"),
                    row.get("Descripiton"),  
                    row.get("Email"),
                    row.get("Phone"),
                    row.get("Website"),
                ),
            )
            inserted += 1
            existing_names.add(normalized_name)

    conn.commit()
    conn.close()
    print(
        "Database populated successfully. "
        f"Inserted={inserted}, "
        f"Skipped blank names={skipped_blank}, "
        f"Skipped duplicates={skipped_duplicate}"
    )


if __name__ == "__main__":
    populate_E3_database()