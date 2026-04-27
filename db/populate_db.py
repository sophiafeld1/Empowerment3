import sqlite3
from pathlib import Path

import pandas as pd


def populate_E3_database():
    base_dir = Path(__file__).resolve().parent
    xlsx_path = (
        base_dir.parent / "data" / "E3_Consolidated_Research_List_with_Past_E3_Engagement.xlsx"
    )
    db_path = base_dir / "E3_database.db"
    table_name = "possible_sponsors"

    write_columns = [
        "name",
        "industry",
        "description",
        "goods_and_services",
        "services_to_E3",
        "E3_provides",
        "email",
        "phone",
        "contact_info",
        "website",
        "city",
        "state",
        "zip",
        "physical_location",
        "geographical_priorities",
        "company_size",
        "giving_priorities",
        "jmu_affiliated",
        "past_e3_engagement",
        "sponsor_capacity_level",
        "recommended_ask_level",
        "classification_confidence",
        "classification_reason",
        "classification_last_updated",
        "manual_override",
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    inserted = 0
    skipped_blank = 0

    df = pd.read_excel(xlsx_path)

    existing_classification_by_name: dict[str, dict] = {}
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    )
    if cursor.fetchone():
        cursor.execute(
            f"""
            SELECT
                name,
                services_to_E3,
                E3_provides,
                sponsor_capacity_level,
                recommended_ask_level,
                classification_confidence,
                classification_reason,
                classification_last_updated,
                manual_override
            FROM {table_name}
            """
        )
        for row in cursor.fetchall():
            row_name = (row[0] or "").strip().lower()
            if row_name:
                existing_classification_by_name[row_name] = {
                    "services_to_E3": row[1],
                    "E3_provides": row[2],
                    "sponsor_capacity_level": row[3],
                    "recommended_ask_level": row[4],
                    "classification_confidence": row[5],
                    "classification_reason": row[6],
                    "classification_last_updated": row[7],
                    "manual_override": row[8],
                }

    # Replace mode: wipe existing sponsors and repopulate from spreadsheet.
    cursor.execute(f"DELETE FROM {table_name}")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))

    insert_sql = f"""
        INSERT INTO {table_name} ({", ".join(write_columns)})
        VALUES ({", ".join("?" for _ in write_columns)})
    """
    def clean_text(value):
        if pd.isna(value):
            return None
        text = str(value).strip()
        return text if text else None

    def clean_int(value):
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def row_value(row, *keys):
        for key in keys:
            if key in row and not pd.isna(row[key]):
                return row[key]
        return None

    for _, row in df.iterrows():
        name = clean_text(row_value(row, "name", "Name"))
        if not name:
            skipped_blank += 1
            continue

        values = [
            name,
            clean_text(row_value(row, "industry", "Industry")),
            clean_text(row_value(row, "description", "Description")),
            clean_text(row_value(row, "goods_and_services", "Goods/Services")),
            clean_text(row_value(row, "services_to_E3", "services_to_E3"))
            or existing_classification_by_name.get(name.lower(), {}).get("services_to_E3"),
            clean_text(row_value(row, "E3_provides", "E3_provides"))
            or existing_classification_by_name.get(name.lower(), {}).get("E3_provides"),
            clean_text(row_value(row, "email", "Email")),
            clean_text(row_value(row, "phone", "Phone")),
            clean_text(row_value(row, "contact_info", "contact_info")),
            clean_text(row_value(row, "website", "Website")),
            clean_text(row_value(row, "city", "City")),
            clean_text(row_value(row, "state", "State")),
            clean_int(row_value(row, "zip", "Zip")),
            clean_int(
                row_value(
                    row,
                    "physical_location",
                    "Physical Location (0 for no, 1 for yes)",
                )
            ),
            clean_text(row_value(row, "geographical_priorities", "geographical_priorities")),
            clean_text(row_value(row, "company_size", "company_size")),
            clean_text(row_value(row, "giving_priorities", "giving_priorities")),
            clean_int(row_value(row, "jmu_affiliated", "jmu_affiliated")),
            clean_text(row_value(row, "past_e3_engagement", "past_e3_engagement")),
            existing_classification_by_name.get(name.lower(), {}).get("sponsor_capacity_level"),
            existing_classification_by_name.get(name.lower(), {}).get("recommended_ask_level"),
            existing_classification_by_name.get(name.lower(), {}).get("classification_confidence"),
            existing_classification_by_name.get(name.lower(), {}).get("classification_reason"),
            existing_classification_by_name.get(name.lower(), {}).get("classification_last_updated"),
            existing_classification_by_name.get(name.lower(), {}).get("manual_override", 0),
        ]

        cursor.execute(insert_sql, tuple(values))
        inserted += 1

    conn.commit()
    conn.close()
    print(
        "Database replace complete. "
        f"Inserted={inserted}, "
        f"Skipped blank names={skipped_blank}, "
    )


if __name__ == "__main__":
    populate_E3_database()