from pathlib import Path
import sqlite3
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from db.main import E3Database
E3Database().create_or_update_schema()

from classification_logic import build_email_generation_fields, classify_sponsor_row
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
    "sponsor_capacity_level",
    "recommended_ask_level",
    "classification_confidence",
    "classification_reason",
    "classification_last_updated",
    "manual_override",
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


CLASSIFICATION_FIELDS = [
    "services_to_E3",
    "E3_provides",
    "sponsor_capacity_level",
    "recommended_ask_level",
    "classification_confidence",
    "classification_reason",
    "classification_last_updated",
]


def _is_non_empty(value) -> bool:
    if value is None:
        return False
    return str(value).strip() != ""


def classify_sponsor_record(sponsor_id: int, *, force_recalculate: bool = False) -> tuple[bool, str]:
    sponsor = get_sponsor_by_id(sponsor_id)
    if not sponsor:
        return False, "Sponsor not found."

    if sponsor.get("manual_override") == 1:
        return False, "Skipped because manual_override is enabled for this sponsor."

    has_existing = any(_is_non_empty(sponsor.get(field)) for field in CLASSIFICATION_FIELDS)
    if has_existing and not force_recalculate:
        return (
            False,
            "Skipped because classification fields already contain values. Use force recalculate to overwrite.",
        )

    updates = classify_sponsor_row(sponsor)
    sponsor.update(updates)
    update_sponsor(sponsor_id, sponsor)
    return True, "Classification updated."


def classify_all_sponsors(*, force_recalculate: bool = False) -> tuple[int, int]:
    options = get_sponsor_options()
    updated = 0
    skipped = 0
    for sponsor_id, _ in options:
        ok, _ = classify_sponsor_record(sponsor_id, force_recalculate=force_recalculate)
        if ok:
            updated += 1
        else:
            skipped += 1
    return updated, skipped


def classification_diff_for_row(row: dict) -> tuple[dict, dict]:
    proposed = classify_sponsor_row(row)
    changes = {}
    for field in CLASSIFICATION_FIELDS:
        old_value = row.get(field)
        new_value = proposed.get(field)
        if str(old_value or "") != str(new_value or ""):
            changes[field] = {"current": old_value, "proposed": new_value}
    return proposed, changes


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
    sponsor_capacity_level,
    recommended_ask_level,
    classification_confidence,
    classification_reason,
    classification_last_updated,
    manual_override,
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
        "sponsor_capacity_level": clean_value(sponsor_capacity_level),
        "recommended_ask_level": clean_value(recommended_ask_level),
        "classification_confidence": clean_value(classification_confidence),
        "classification_reason": clean_value(classification_reason),
        "classification_last_updated": clean_value(classification_last_updated),
        "manual_override": clean_zero_one(manual_override),
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

    def pick_index(value: str, options: list[str]) -> int:
        return options.index(value) if value in options else 0

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
        capacity_options = ["", "High", "Medium", "Low", "Unknown"]
        sponsor_capacity_level = st.selectbox(
            "Sponsor capacity level",
            options=capacity_options,
            index=pick_index(gv("sponsor_capacity_level"), capacity_options),
            key=f"{ks}_capacity",
        )
        ask_options = ["", "Large ask", "Moderate ask", "Small ask", "Flexible ask"]
        recommended_ask_level = st.selectbox(
            "Recommended ask level",
            options=ask_options,
            index=pick_index(gv("recommended_ask_level"), ask_options),
            key=f"{ks}_ask",
        )
        confidence_options = [
            "",
            "High confidence",
            "Medium confidence",
            "Low confidence",
            "Unknown confidence",
        ]
        classification_confidence = st.selectbox(
            "Classification confidence",
            options=confidence_options,
            index=pick_index(gv("classification_confidence"), confidence_options),
            key=f"{ks}_confidence",
        )
        classification_reason = st.text_area(
            "Classification reason",
            value=gv("classification_reason"),
            height=100,
            key=f"{ks}_reason",
        )
        classification_last_updated = st.text_input(
            "Classification last updated",
            value=gv("classification_last_updated"),
            key=f"{ks}_updated",
        )
        manual_override_default = 1 if s and s.get("manual_override") == 1 else 0
        manual_override = st.selectbox(
            "Manual override (0 = off, 1 = on)",
            options=[0, 1],
            index=manual_override_default,
            key=f"{ks}_override",
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
        sponsor_capacity_level,
        recommended_ask_level,
        classification_confidence,
        classification_reason,
        classification_last_updated,
        manual_override,
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
    if "email_context_preview" not in st.session_state:
        st.session_state.email_context_preview = None

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
                description=selected.get("description"),
                goods_and_services=selected.get("goods_and_services"),
                services_to_e3=selected.get("services_to_E3"),
                city=selected.get("city"),
                state=selected.get("state"),
                geographical_priorities=selected.get("geographical_priorities"),
                giving_priorities=selected.get("giving_priorities"),
                past_e3_engagement=selected.get("past_e3_engagement"),
                jmu_affiliated=selected.get("jmu_affiliated"),
                e3_provides=selected.get("E3_provides"),
                website=selected.get("website"),
                contact_info=selected.get("contact_info"),
                sponsor_capacity_level=selected.get("sponsor_capacity_level"),
                recommended_ask_level=selected.get("recommended_ask_level"),
                classification_reason=selected.get("classification_reason"),
            )
            st.session_state.email_draft_text = generate_email_draft(sponsor, email_type)

    if st.sidebar.button("Preview email fields"):
        selected = get_sponsor_by_id(selected_id)
        if selected:
            st.session_state.email_context_preview = build_email_generation_fields(selected)

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

    if st.session_state.email_context_preview:
        st.sidebar.caption("Email generation fields")
        st.sidebar.json(st.session_state.email_context_preview)


def render_classification_sidebar():
    st.sidebar.header("Sponsor Classification")
    options = get_sponsor_options()
    if not options:
        st.sidebar.info("No sponsors found.")
        return

    option_labels = {f"{name} (ID {sponsor_id})": sponsor_id for sponsor_id, name in options}
    selected_label = st.sidebar.selectbox(
        "Sponsor to classify",
        list(option_labels.keys()),
        key="classification_selected_sponsor",
    )
    selected_id = option_labels[selected_label]
    force_recalculate = st.sidebar.checkbox(
        "Force recalculate existing values",
        value=False,
        key="classification_force_recalculate",
    )

    if st.sidebar.button("Classify selected sponsor"):
        ok, message = classify_sponsor_record(
            selected_id,
            force_recalculate=force_recalculate,
        )
        if ok:
            st.sidebar.success(message)
        else:
            st.sidebar.warning(message)

    if st.sidebar.button("Classify all sponsors"):
        updated, skipped = classify_all_sponsors(force_recalculate=force_recalculate)
        st.sidebar.success(f"Updated: {updated} | Skipped: {skipped}")


def _parse_multi_value_field(series: pd.Series) -> list[str]:
    values: set[str] = set()
    for raw in series.dropna():
        for part in str(raw).split(","):
            clean = part.strip()
            if clean:
                values.add(clean)
    return sorted(values)


def render_sponsor_search_page():
    st.header("Empowerment3 Sponsor Search")
    sponsors_df = get_all_sponsors("")
    if sponsors_df.empty:
        st.info("No sponsors found.")
        return

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        name_query = st.text_input("Name/industry contains", key="search_name_query")
        capacity_filter = st.multiselect(
            "Capacity level",
            options=sorted(
                [v for v in sponsors_df["sponsor_capacity_level"].dropna().astype(str).unique() if v.strip()]
            ),
            key="search_capacity_filter",
        )
    with filter_col2:
        confidence_filter = st.multiselect(
            "Confidence level",
            options=sorted(
                [v for v in sponsors_df["classification_confidence"].dropna().astype(str).unique() if v.strip()]
            ),
            key="search_confidence_filter",
        )
        e3_provides_options = _parse_multi_value_field(sponsors_df["E3_provides"])
        e3_provides_filter = st.multiselect(
            "E3 provides includes",
            options=e3_provides_options,
            key="search_e3_provides_filter",
        )
    with filter_col3:
        services_options = _parse_multi_value_field(sponsors_df["services_to_E3"])
        services_filter = st.multiselect(
            "Services to E3 includes",
            options=services_options,
            key="search_services_filter",
        )
        area_query = st.text_input(
            "Area (city/state/geographical priorities)",
            key="search_area_query",
        )

    filtered = sponsors_df.copy()
    if name_query.strip():
        q = name_query.strip().lower()
        filtered = filtered[
            filtered["name"].fillna("").str.lower().str.contains(q)
            | filtered["industry"].fillna("").str.lower().str.contains(q)
        ]
    if capacity_filter:
        filtered = filtered[filtered["sponsor_capacity_level"].fillna("").isin(capacity_filter)]
    if confidence_filter:
        filtered = filtered[filtered["classification_confidence"].fillna("").isin(confidence_filter)]
    if e3_provides_filter:
        filtered = filtered[
            filtered["E3_provides"].fillna("").apply(
                lambda raw: all(
                    selected in [part.strip() for part in str(raw).split(",") if part.strip()]
                    for selected in e3_provides_filter
                )
            )
        ]
    if services_filter:
        filtered = filtered[
            filtered["services_to_E3"].fillna("").apply(
                lambda raw: all(
                    selected in [part.strip() for part in str(raw).split(",") if part.strip()]
                    for selected in services_filter
                )
            )
        ]
    if area_query.strip():
        q = area_query.strip().lower()
        filtered = filtered[
            filtered["city"].fillna("").str.lower().str.contains(q)
            | filtered["state"].fillna("").str.lower().str.contains(q)
            | filtered["geographical_priorities"].fillna("").str.lower().str.contains(q)
        ]

    st.caption(f"Rows matched: {len(filtered)}")
    st.dataframe(filtered, use_container_width=True, hide_index=True)


def render_generate_emails_tab():
    st.header("Generate Emails")
    options = get_sponsor_options()
    if not options:
        st.info("No sponsors found.")
        return

    service_to_email_types = {
        "gift card / donation of goods/service": ["gift_card"],
        "monetary donation": ["fundraising"],
        "partnership, one-time or ongoing": [
            "partnership_event",
            "partnership_accessibility",
        ],
        "Flexible ask": EMAIL_TYPES,
    }

    option_labels = {f"{name} (ID {sponsor_id})": sponsor_id for sponsor_id, name in options}
    selected_label = st.selectbox("Select business", list(option_labels.keys()), key="email_tab_sponsor")
    selected_id = option_labels[selected_label]
    selected = get_sponsor_by_id(selected_id)

    allowed_email_types: list[str] = []
    if selected:
        raw_services = selected.get("services_to_E3") or ""
        service_parts = [part.strip() for part in str(raw_services).split(",") if part.strip()]
        for service in service_parts:
            for email_type in service_to_email_types.get(service, []):
                if email_type not in allowed_email_types:
                    allowed_email_types.append(email_type)

    if not allowed_email_types:
        allowed_email_types = EMAIL_TYPES[:]
        st.caption(
            "No specific services_to_E3 mapping found for this sponsor, so all email types are available."
        )
    else:
        st.caption(
            "Email types are limited to options that match this sponsor's services_to_E3 classification."
        )

    email_type = st.selectbox(
        "Select email type",
        allowed_email_types,
        key="email_tab_type",
    )

    if st.button("Generate email", key="email_tab_generate"):
        if selected:
            sponsor = Sponsor(
                name=selected.get("name") or "",
                industry=selected.get("industry"),
                description=selected.get("description"),
                goods_and_services=selected.get("goods_and_services"),
                services_to_e3=selected.get("services_to_E3"),
                city=selected.get("city"),
                state=selected.get("state"),
                geographical_priorities=selected.get("geographical_priorities"),
                giving_priorities=selected.get("giving_priorities"),
                past_e3_engagement=selected.get("past_e3_engagement"),
                jmu_affiliated=selected.get("jmu_affiliated"),
                e3_provides=selected.get("E3_provides"),
                website=selected.get("website"),
                contact_info=selected.get("contact_info"),
                sponsor_capacity_level=selected.get("sponsor_capacity_level"),
                recommended_ask_level=selected.get("recommended_ask_level"),
                classification_reason=selected.get("classification_reason"),
            )
            st.session_state.email_draft_text = generate_email_draft(sponsor, email_type)
            st.session_state.email_context_preview = build_email_generation_fields(selected)

    if st.session_state.get("email_context_preview"):
        with st.expander("Email generation fields"):
            st.json(st.session_state.email_context_preview)

    if st.session_state.get("email_draft_text"):
        st.subheader("Generated Email Draft")
        st.text_area("Draft", value=st.session_state.email_draft_text, height=340)
        render_copy_button(st.session_state.email_draft_text)


def main():
    st.set_page_config(page_title="E3 Sponsor Database", layout="wide")
    st.title("E3 Sponsor Database")
    st.caption("Sponsor management, search, and outreach drafting")
    if "edit_classification_preview" not in st.session_state:
        st.session_state.edit_classification_preview = None
    if "email_draft_text" not in st.session_state:
        st.session_state.email_draft_text = None
    if "email_context_preview" not in st.session_state:
        st.session_state.email_context_preview = None

    search_tab, email_tab, manage_tab = st.tabs(
        ["Empowerment3 Sponsor Search", "Generate Emails", "Manage Sponsors"]
    )

    with search_tab:
        render_sponsor_search_page()

    with email_tab:
        render_generate_emails_tab()

    with manage_tab:
        mode = st.radio("Mode", ["Add Sponsor", "Edit Sponsor"], horizontal=True)

        classify_controls_col1, classify_controls_col2 = st.columns(2)
        with classify_controls_col1:
            st.markdown("#### Sponsor Classification Controls")
            options = get_sponsor_options()
            if options:
                option_labels = {f"{name} (ID {sponsor_id})": sponsor_id for sponsor_id, name in options}
                selected_label = st.selectbox(
                    "Sponsor to classify",
                    list(option_labels.keys()),
                    key="classification_selected_sponsor_main",
                )
                selected_id_for_classification = option_labels[selected_label]
                force_recalculate = st.checkbox(
                    "Force recalculate existing values",
                    value=False,
                    key="classification_force_recalculate_main",
                )
                if st.button("Classify selected sponsor", key="classify_selected_main"):
                    ok, message = classify_sponsor_record(
                        selected_id_for_classification,
                        force_recalculate=force_recalculate,
                    )
                    if ok:
                        st.success(message)
                    else:
                        st.warning(message)
                if st.button("Classify all sponsors", key="classify_all_main"):
                    updated, skipped = classify_all_sponsors(force_recalculate=force_recalculate)
                    st.success(f"Updated: {updated} | Skipped: {skipped}")

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

                preview_col, apply_col = st.columns(2)
                with preview_col:
                    if st.button("Preview recalculation", key=f"preview_classification_{selected_id}"):
                        if selected and selected.get("manual_override") == 1:
                            st.session_state.edit_classification_preview = {
                                "sponsor_id": selected_id,
                                "blocked": True,
                                "message": "manual_override is enabled; disable it first to recalculate.",
                            }
                        elif selected:
                            proposed, changes = classification_diff_for_row(selected)
                            st.session_state.edit_classification_preview = {
                                "sponsor_id": selected_id,
                                "blocked": False,
                                "proposed": proposed,
                                "changes": changes,
                            }

                with apply_col:
                    if st.button("Apply recalculation", key=f"apply_classification_{selected_id}"):
                        preview = st.session_state.edit_classification_preview
                        if not selected:
                            st.warning("No sponsor selected.")
                        elif selected.get("manual_override") == 1:
                            st.warning("manual_override is enabled; disable it first to recalculate.")
                        elif not preview or preview.get("sponsor_id") != selected_id:
                            st.warning("Preview changes first, then apply.")
                        elif preview.get("blocked"):
                            st.warning(preview.get("message") or "Cannot apply recalculation.")
                        else:
                            updated_values = dict(selected)
                            updated_values.update(preview.get("proposed", {}))
                            update_sponsor(selected_id, updated_values)
                            st.success("Classification recalculation applied.")
                            st.session_state.edit_classification_preview = None
                            st.rerun()

                preview = st.session_state.edit_classification_preview
                if preview and preview.get("sponsor_id") == selected_id:
                    st.markdown("#### Classification Recalculation Preview")
                    if preview.get("blocked"):
                        st.warning(preview.get("message") or "Recalculation blocked.")
                    else:
                        changes = preview.get("changes", {})
                        if not changes:
                            st.info("No classification changes would be made.")
                        else:
                            st.dataframe(
                                [
                                    {
                                        "field": field,
                                        "current": diff["current"],
                                        "proposed": diff["proposed"],
                                    }
                                    for field, diff in changes.items()
                                ],
                                use_container_width=True,
                                hide_index=True,
                            )

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
        search = st.text_input("Search by name or industry", key="manage_search")
        sponsors_df = get_all_sponsors(search)
        st.dataframe(sponsors_df, use_container_width=True, hide_index=True)
        st.caption(f"Rows shown: {len(sponsors_df)}")


if __name__ == "__main__":
    main()
