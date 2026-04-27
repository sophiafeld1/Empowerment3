from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "db" / "E3_database.db"
TABLE_NAME = "possible_sponsors"
DEFAULT_COLUMNS = ["id", "name", "industry", "email", "phone", "city", "state"]


def build_query(search: str | None, selected_columns: list[str]) -> tuple[str, list[str]]:
    cols_sql = ", ".join(selected_columns)
    query = f"SELECT {cols_sql} FROM {TABLE_NAME}"
    params: list[str] = []
    if search and search.strip():
        query += " WHERE LOWER(name) LIKE ? OR LOWER(industry) LIKE ?"
        pattern = f"%{search.strip().lower()}%"
        params.extend([pattern, pattern])
    query += " ORDER BY name ASC"
    return query, params


def _truncate(text: str, width: int) -> str:
    if width < 2:
        return text[:width]
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _fit_widths_to_terminal(widths: list[int], max_total: int) -> list[int]:
    total = sum(widths) + (3 * (len(widths) - 1))
    if total <= max_total:
        return widths

    adjusted = widths[:]
    minimum = 8
    while total > max_total:
        shrinkable = [i for i, w in enumerate(adjusted) if w > minimum]
        if not shrinkable:
            break
        idx = max(shrinkable, key=lambda i: adjusted[i])
        adjusted[idx] -= 1
        total -= 1
    return adjusted


def format_table(headers: list[str], rows: list[sqlite3.Row], max_width: int) -> str:
    if not rows:
        return "No rows found."

    values = [[str(row[h]) if row[h] is not None else "" for h in headers] for row in rows]
    widths = [len(h) for h in headers]
    for row in values:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    widths = [min(w, 40) for w in widths]
    widths = _fit_widths_to_terminal(widths, max_width)

    header_line = " | ".join(_truncate(h, widths[i]).ljust(widths[i]) for i, h in enumerate(headers))
    divider = "-+-".join("-" * widths[i] for i in range(len(headers)))
    data_lines = [
        " | ".join(_truncate(cell, widths[i]).ljust(widths[i]) for i, cell in enumerate(row))
        for row in values
    ]
    return "\n".join([header_line, divider, *data_lines])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="View E3 sponsor database records from terminal."
    )
    parser.add_argument(
        "--search",
        type=str,
        default="",
        help="Case-insensitive name/industry search filter.",
    )
    parser.add_argument(
        "--columns",
        type=str,
        default=",".join(DEFAULT_COLUMNS),
        help="Comma-separated columns to show (default is compact terminal view).",
    )
    parser.add_argument(
        "--all-columns",
        action="store_true",
        help="Display all database columns.",
    )
    args = parser.parse_args()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(f"PRAGMA table_info({TABLE_NAME})")
    all_headers = [row[1] for row in cur.fetchall()]
    if args.all_columns:
        selected_columns = all_headers
    else:
        requested = [col.strip() for col in args.columns.split(",") if col.strip()]
        invalid = [col for col in requested if col not in all_headers]
        if invalid:
            conn.close()
            raise SystemExit(f"Unknown columns: {', '.join(invalid)}")
        selected_columns = requested or DEFAULT_COLUMNS

    query, params = build_query(args.search, selected_columns)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    terminal_width = shutil.get_terminal_size(fallback=(120, 20)).columns
    print(format_table(selected_columns, rows, terminal_width))
    print(f"\nRows shown: {len(rows)}")


if __name__ == "__main__":
    main()
