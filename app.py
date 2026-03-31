from pathlib import Path
import sqlite3
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from email_logic.email_templates import Sponsor, EMAIL_TYPES, generate_email_draft


DB_PATH = Path(__file__).resolve().parent / "db" / "E3_database.db"
TABLE_NAME = "possible_sponsors"


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


def insert_sponsor(
    name: str,
    industry: str,
    description: str,
    email: str,
    phone: str,
    website: str,
    city: str,
    state: str,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO {TABLE_NAME}
        (name, industry, description, email, phone, website, city, state)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, industry, description, email, phone, website, city, state),
    )
    conn.commit()
    conn.close()


def get_sponsor_options():
    conn = get_connection()
    query = f"SELECT id, name FROM {TABLE_NAME} ORDER BY name ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def get_sponsor_by_id(sponsor_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT id, name, industry, description, email, phone, website, city, state, E3_provides
        FROM {TABLE_NAME}
        WHERE id = ?
        """,
        (sponsor_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_sponsor(
    sponsor_id: int,
    name: str,
    industry: str,
    description: str,
    email: str,
    phone: str,
    website: str,
    city: str,
    state: str,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE {TABLE_NAME}
        SET name = ?, industry = ?, description = ?, email = ?, phone = ?, website = ?, city = ?, state = ?
        WHERE id = ?
        """,
        (name, industry, description, email, phone, website, city, state, sponsor_id),
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
        sponsor = Sponsor(
            name=selected[1] or "",
            industry=selected[2],
            city=selected[7],
            state=selected[8],
            e3_provides=selected[9],
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
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name *")
                industry = st.text_input("Industry")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
            with col2:
                website = st.text_input("Website")
                city = st.text_input("City")
                state = st.text_input("State")
                description = st.text_area("Description", height=100)

            submitted = st.form_submit_button("Save Sponsor")

        if submitted:
            clean_name = clean_value(name)
            if not clean_name:
                st.error("Name is required.")
            elif sponsor_exists(clean_name):
                st.warning("A sponsor with this name already exists.")
            else:
                insert_sponsor(
                    name=clean_name,
                    industry=clean_value(industry),
                    description=clean_value(description),
                    email=clean_value(email),
                    phone=clean_value(phone),
                    website=clean_value(website),
                    city=clean_value(city),
                    state=clean_value(state),
                )
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
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Name *", value=selected[1] or "")
                    industry = st.text_input("Industry", value=selected[2] or "")
                    email = st.text_input("Email", value=selected[4] or "")
                    phone = st.text_input("Phone", value=selected[5] or "")
                with col2:
                    website = st.text_input("Website", value=selected[6] or "")
                    city = st.text_input("City", value=selected[7] or "")
                    state = st.text_input("State", value=selected[8] or "")
                    description = st.text_area("Description", value=selected[3] or "", height=100)

                update_submitted = st.form_submit_button("Update Sponsor")

            if update_submitted:
                clean_name = clean_value(name)
                if not clean_name:
                    st.error("Name is required.")
                elif sponsor_name_exists_for_other_id(clean_name, selected_id):
                    st.warning("Another sponsor already uses this name.")
                else:
                    update_sponsor(
                        sponsor_id=selected_id,
                        name=clean_name,
                        industry=clean_value(industry),
                        description=clean_value(description),
                        email=clean_value(email),
                        phone=clean_value(phone),
                        website=clean_value(website),
                        city=clean_value(city),
                        state=clean_value(state),
                    )
                    st.success("Sponsor updated.")

    st.divider()
    st.subheader("Current Sponsors")
    search = st.text_input("Search by name or industry")
    sponsors_df = get_all_sponsors(search)
    st.dataframe(sponsors_df, use_container_width=True, hide_index=True)
    st.caption(f"Rows shown: {len(sponsors_df)}")


if __name__ == "__main__":
    main()
