from pathlib import Path
import sqlite3
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from db.main import E3Database
E3Database().create_or_update_schema()

from email_logic.email_templates import Sponsor, EMAIL_TYPES, generate_email_draft


DB_PATH = Path(__file__).resolve().parent / "db" / "E3_database.db"
TABLE_NAME = "possible_sponsors"

# Columns for insert/update (excluding id).
SPONSOR_WRITE_COLUMNS = [
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
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_all_sponsors(search_text: str = "") -> pd.DataFrame:
    conn = get_connection()
    query = f"SELECT * FROM {TABLE_NAME}"
    params = []
    if search_text.strip():
        query += " WHERE LOWER(name) LIKE ? OR LOWER(industry) LIKE ?"
        pattern = f"%{search_text.strip().lower()}%"
        params = [pattern, pattern]
    query += " ORDER BY name ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def sponsor_exists(name: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT 1 FROM {TABLE_NAME} WHERE LOWER(name) = LOWER(?) LIMIT 1",
        (name.strip(),),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def insert_sponsor(values: dict):
    cols = ", ".join(SPONSOR_WRITE_COLUMNS)
    placeholders = ", ".join(["?"] * len(SPONSOR_WRITE_COLUMNS))
    tuple_vals = tuple(values[c] for c in SPONSOR_WRITE_COLUMNS)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO {TABLE_NAME} ({cols}) VALUES ({placeholders})",
        tuple_vals,
    )
    conn.commit()
    conn.close()


def get_sponsor_options():
    conn = get_connection()
    query = f"SELECT id, name FROM {TABLE_NAME} ORDER BY name ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def get_sponsor_by_id(sponsor_id: int) -> dict | None:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (sponsor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_sponsor(sponsor_id: int, values: dict):
    assignments = ", ".join(f"{c} = ?" for c in SPONSOR_WRITE_COLUMNS)
    tuple_vals = tuple(values[c] for c in SPONSOR_WRITE_COLUMNS) + (sponsor_id,)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE {TABLE_NAME} SET {assignments} WHERE id = ?",
        tuple_vals,
    )
    conn.commit()
    conn.close()


def sponsor_name_exists_for_other_id(name: str, sponsor_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT 1
        FROM {TABLE_NAME}
        WHERE LOWER(name) = LOWER(?) AND id != ?
        LIMIT 1
        """,
        (name.strip(), sponsor_id),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def clean_value(value: str):
    value = (value or "").strip()
    return value if value else None


def clean_zip(value: str):
    v = clean_value(value)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def clean_zero_one(value):
    if value in (1, "1", True):
        return 1
    if value in (0, "0", False):
        return 0
    return None


def sponsor_form_values(
    name,
    industry,
    description,
    goods_and_services,
    services_to_E3,
    e3_provides,
    email,
    phone,
    contact_info,
    website,
    city,
    state,
    zip_raw,
    physical_location,
    geographical_priorities,
    company_size,
    giving_priorities,
    jmu_affiliated,
    past_e3_engagement,
) -> dict:
    return {
        "name": clean_value(name),
        "industry": clean_value(industry),
        "description": clean_value(description),
        "goods_and_services": clean_value(goods_and_services),
        "services_to_E3": clean_value(services_to_E3),
        "E3_provides": clean_value(e3_provides),
        "email": clean_value(email),
        "phone": clean_value(phone),
        "contact_info": clean_value(contact_info),
        "website": clean_value(website),
        "city": clean_value(city),
        "state": clean_value(state),
        "zip": clean_zip(zip_raw),
        "physical_location": clean_zero_one(physical_location),
        "geographical_priorities": clean_value(geographical_priorities),
        "company_size": clean_value(company_size),
        "giving_priorities": clean_value(giving_priorities),
        "jmu_affiliated": clean_zero_one(jmu_affiliated),
        "past_e3_engagement": clean_value(past_e3_engagement),
    }


def render_sponsor_fields(s, prefix: str, *, key_suffix: str = ""):
    """s = dict from DB for edit, or None for add. key_suffix avoids stale widgets when editing another row."""
    ks = f"{prefix}_{key_suffix}" if key_suffix else prefix

    def gv(key, default=""):
        if s is None:
            return default
        val = s.get(key)
        if val is None:
            return default
        return str(val)

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name *", value=gv("name"), key=f"{ks}_name")
        industry = st.text_input("Industry", value=gv("industry"), key=f"{ks}_industry")
        goods_and_services = st.text_area(
            "Goods & services (what they sell / offer)",
            value=gv("goods_and_services"),
            height=80,
            key=f"{ks}_goods",
        )
        description = st.text_area("Description", value=gv("description"), height=80, key=f"{ks}_desc")
        giving_priorities = st.text_area(
            "Giving priorities (who they serve)",
            value=gv("giving_priorities"),
            height=80,
            key=f"{ks}_giving",
        )
        services_to_E3 = st.text_input(
            "Services to E3 (calculated later)",
            value=gv("services_to_E3"),
            key=f"{ks}_s2e3",
        )
        e3_provides = st.text_input(
            "E3 provides (calculated later)",
            value=gv("E3_provides"),
            key=f"{ks}_e3p",
        )
    with col2:
        email = st.text_input("Email", value=gv("email"), key=f"{ks}_email")
        phone = st.text_input("Phone", value=gv("phone"), key=f"{ks}_phone")
        contact_info = st.text_area(
            "Contact info (other / notes)",
            value=gv("contact_info"),
            height=70,
            key=f"{ks}_contact",
        )
        website = st.text_input("Website", value=gv("website"), key=f"{ks}_web")
        physical_location_default = 1 if s and s.get("physical_location") == 1 else 0
        physical_location = st.selectbox(
            "Physical location (0 = no, 1 = yes)",
            options=[0, 1],
            index=physical_location_default,
            key=f"{ks}_phys",
        )
        city = st.text_input("City", value=gv("city"), key=f"{ks}_city")
        state = st.text_input("State", value=gv("state"), key=f"{ks}_state")
        zip_val = st.text_input("Zip", value=gv("zip"), key=f"{ks}_zip")
        geographical_priorities = st.text_input(
            "Geographical priorities (where they give: Valley, Elkton, Harrisonburg...)",
            value=gv("geographical_priorities"),
            key=f"{ks}_geo",
        )
        company_size = st.text_input(
            "Company size (estimate employee count, e.g. LinkedIn)",
            value=gv("company_size"),
            key=f"{ks}_size",
        )
        jmu_default = 1 if s and s.get("jmu_affiliated") == 1 else 0
        jmu_affiliated = st.selectbox(
            "JMU affiliated (0 = no, 1 = yes)",
            options=[0, 1],
            index=jmu_default,
            key=f"{ks}_jmu",
        )
        past_e3_engagement = st.text_input(
            "Past Empowerment3 engagement",
            value=gv("past_e3_engagement"),
            key=f"{ks}_past",
        )

    return (
        name,
        industry,
        description,
        goods_and_services,
        services_to_E3,
        e3_provides,
        email,
        phone,
        contact_info,
        website,
        city,
        state,
        zip_val,
        physical_location,
        geographical_priorities,
        company_size,
        giving_priorities,
        jmu_affiliated,
        past_e3_engagement,
    )


def render_copy_button(text_to_copy: str):
    if st.button("Copy to clipboard"):
        safe_text = json.dumps(text_to_copy)
        components.html(
            f"""
            <script>
            navigator.clipboard.writeText({safe_text});
            </script>
            """,
            height=0,
        )
        st.success("Copied to clipboard.")


def render_email_drafting_sidebar():
    if "email_draft_text" not in st.session_state:
        st.session_state.email_draft_text = None

    st.sidebar.header("Email Sponsor Drafting")
    name_filter = st.sidebar.text_input("Filter sponsors")

    all_options = get_sponsor_options()
    filtered_options = [
        (sponsor_id, name)
        for sponsor_id, name in all_options
        if name_filter.strip().lower() in (name or "").lower()
    ]

    if not filtered_options:
        st.sidebar.info("No matching sponsors.")
        return

    sponsor_labels = {f"{name} (ID {sponsor_id})": sponsor_id for sponsor_id, name in filtered_options}
    selected_label = st.sidebar.selectbox("Select sponsor", list(sponsor_labels.keys()))
    selected_id = sponsor_labels[selected_label]
    email_type = st.sidebar.selectbox("Select type", EMAIL_TYPES)

    if st.sidebar.button("Generate draft"):
        selected = get_sponsor_by_id(selected_id)
        if selected:
            sponsor = Sponsor(
                name=selected.get("name") or "",
                industry=selected.get("industry"),
                city=selected.get("city"),
                state=selected.get("state"),
                e3_provides=selected.get("E3_provides"),
            )
            st.session_state.email_draft_text = generate_email_draft(sponsor, email_type)

    if st.session_state.email_draft_text:
        left_col, right_col = st.columns([5, 1])
        with left_col:
            st.subheader("Generated Email Draft")
        with right_col:
            if st.button("X Close Draft"):
                st.session_state.email_draft_text = None
                st.rerun()

        st.text_area("Draft", value=st.session_state.email_draft_text, height=320)
        render_copy_button(st.session_state.email_draft_text)


def main():
    st.set_page_config(page_title="E3 Sponsor Database", layout="wide")
    st.title("E3 Sponsor Database")
    st.caption("Manual sponsor entry + quick search")
    render_email_drafting_sidebar()

    mode = st.radio("Mode", ["Add Sponsor", "Edit Sponsor"], horizontal=True)

    if mode == "Add Sponsor":
        with st.form("add_sponsor_form", clear_on_submit=True):
            st.subheader("Add Sponsor")
            fields = render_sponsor_fields(None, "add")
            submitted = st.form_submit_button("Save Sponsor")

        if submitted:
            vals = sponsor_form_values(*fields)
            if not vals["name"]:
                st.error("Name is required.")
            elif sponsor_exists(vals["name"]):
                st.warning("A sponsor with this name already exists.")
            else:
                insert_sponsor(vals)
                st.success("Sponsor added.")
    else:
        st.subheader("Edit Sponsor")
        options = get_sponsor_options()
        if not options:
            st.info("No sponsors found yet.")
        else:
            option_labels = {
                f"{name} (ID {sponsor_id})": sponsor_id for sponsor_id, name in options
            }
            selected_label = st.selectbox("Select sponsor", list(option_labels.keys()))
            selected_id = option_labels[selected_label]
            selected = get_sponsor_by_id(selected_id)

            with st.form("edit_sponsor_form"):
                fields = render_sponsor_fields(
                    selected, "edit", key_suffix=str(selected_id)
                )
                update_submitted = st.form_submit_button("Update Sponsor")

            if update_submitted and selected:
                vals = sponsor_form_values(*fields)
                if not vals["name"]:
                    st.error("Name is required.")
                elif sponsor_name_exists_for_other_id(vals["name"], selected_id):
                    st.warning("Another sponsor already uses this name.")
                else:
                    update_sponsor(selected_id, vals)
                    st.success("Sponsor updated.")

    st.divider()
    st.subheader("Current Sponsors")
    search = st.text_input("Search by name or industry")
    sponsors_df = get_all_sponsors(search)
    st.dataframe(sponsors_df, use_container_width=True, hide_index=True)
    st.caption(f"Rows shown: {len(sponsors_df)}")


if __name__ == "__main__":
    main()
