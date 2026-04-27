from __future__ import annotations

from datetime import datetime, timezone


CAPACITY_TO_ASK = {
    "High": "Large ask",
    "Medium": "Moderate ask",
    "Low": "Small ask",
    "Unknown": "Flexible ask",
}


HIGH_CAPACITY_KEYWORDS = {
    "car dealership",
    "dealership",
    "bank",
    "credit union",
    "hospital",
    "healthcare system",
    "medical center",
    "resort",
    "university",
    "regional",
    "national",
    "foundation",
    "sponsorship",
    "donation program",
    "community giving",
    "entertainment company",
    "major recreation",
    "large venue",
    "toyota",
    "chrysler",
}

MEDIUM_CAPACITY_KEYWORDS = {
    "restaurant",
    "brewery",
    "winery",
    "cidery",
    "distillery",
    "gym",
    "fitness",
    "sports",
    "recreation",
    "event venue",
    "cafe",
    "hospitality",
    "professional service",
}

LOW_CAPACITY_KEYWORDS = {
    "coffee shop",
    "small business",
    "boutique",
    "vendor",
    "farmers market",
    "student group",
    "club",
    "small nonprofit",
    "craft",
    "individual-owned",
}

GOODS_SERVICE_KEYWORDS = {
    "restaurant",
    "cafe",
    "coffee",
    "brewery",
    "winery",
    "cidery",
    "retail",
    "salon",
    "spa",
    "entertainment",
    "sports",
    "recreation",
    "gym",
    "fitness",
    "hotel",
    "resort",
    "shop",
    "vendor",
    "bakery",
}

MONETARY_KEYWORDS = {
    "dealership",
    "bank",
    "credit union",
    "healthcare",
    "hospital",
    "corporation",
    "regional",
    "national",
    "foundation",
    "financial",
    "institution",
    "resort",
    "university",
    "sponsorship",
    "donation program",
    "community giving",
}

PARTNERSHIP_KEYWORDS = {
    "nonprofit",
    "community",
    "youth",
    "family",
    "veteran",
    "disabil",
    "older adult",
    "refugee",
    "student",
    "school",
    "education",
    "wellness",
    "recreation",
    "hospitality",
    "accessib",
    "event",
    "program",
}


def _clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "nan"} else text


def _text_blob(row: dict) -> str:
    parts = [
        _clean_text(row.get("name")),
        _clean_text(row.get("industry")),
        _clean_text(row.get("description")),
        _clean_text(row.get("goods_and_services")),
        _clean_text(row.get("giving_priorities")),
        _clean_text(row.get("geographical_priorities")),
        _clean_text(row.get("website")),
        _clean_text(row.get("past_e3_engagement")),
    ]
    return " | ".join(parts).lower()


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _capacity_from_rules(text: str) -> tuple[str, str]:
    if _contains_any(text, HIGH_CAPACITY_KEYWORDS):
        return "High", "matched high-capacity organization indicators"
    if _contains_any(text, MEDIUM_CAPACITY_KEYWORDS):
        return "Medium", "matched established local business indicators"
    if _contains_any(text, LOW_CAPACITY_KEYWORDS):
        return "Low", "matched small-business or vendor indicators"
    return "Unknown", "insufficient row details for capacity classification"


def _services_to_e3(text: str, row: dict, capacity_level: str) -> list[str]:
    services: list[str] = []
    if _contains_any(text, GOODS_SERVICE_KEYWORDS):
        services.append("gift card / donation of goods/service")
    if _contains_any(text, MONETARY_KEYWORDS) or capacity_level == "High":
        services.append("monetary donation")
    if _contains_any(text, PARTNERSHIP_KEYWORDS) or row.get("physical_location") == 1:
        services.append("partnership, one-time or ongoing")
    if not services:
        services.append("Flexible ask")
    return services


def _e3_provides(text: str, row: dict) -> list[str]:
    values: list[str] = []
    if _contains_any(text, GOODS_SERVICE_KEYWORDS | MEDIUM_CAPACITY_KEYWORDS | LOW_CAPACITY_KEYWORDS):
        values.append("visibility")
    if row.get("physical_location") == 1 or _contains_any(
        text, {"hospitality", "event", "recreation", "fitness", "school", "venue", "public"}
    ):
        values.append("more inclusive / accessible")
    if _contains_any(
        text,
        {
            "nonprofit",
            "community",
            "school",
            "health",
            "youth",
            "family",
            "veteran",
            "disabil",
            "giving",
            "local",
        },
    ):
        values.append("helping out the community")
    if not values:
        values.append("Unknown")
    return values


def _confidence_level(row: dict, text: str, capacity_level: str) -> str:
    if capacity_level == "Unknown":
        return "Unknown confidence"
    data_points = 0
    for field in ("industry", "description", "goods_and_services", "city", "state"):
        if _clean_text(row.get(field)):
            data_points += 1
    if data_points >= 3:
        return "High confidence"
    if data_points >= 2 or _contains_any(text, HIGH_CAPACITY_KEYWORDS | MEDIUM_CAPACITY_KEYWORDS):
        return "Medium confidence"
    return "Low confidence"


def _classification_reason(
    capacity_level: str, capacity_reason: str, services_to_e3: list[str], e3_provides: list[str]
) -> str:
    services_text = ", ".join(services_to_e3)
    e3_text = ", ".join(e3_provides)
    return (
        f"Classified as {capacity_level} capacity because row data {capacity_reason}. "
        f"Recommended sponsor contribution types: {services_text}. "
        f"Recommended E3 value exchange: {e3_text}."
    )


def classify_sponsor_row(row: dict) -> dict:
    text = _text_blob(row)
    capacity_level, capacity_reason = _capacity_from_rules(text)
    recommended_ask_level = CAPACITY_TO_ASK[capacity_level]
    services_to_e3 = _services_to_e3(text, row, capacity_level)
    e3_provides = _e3_provides(text, row)
    confidence = _confidence_level(row, text, capacity_level)
    reason = _classification_reason(capacity_level, capacity_reason, services_to_e3, e3_provides)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return {
        "services_to_E3": ", ".join(services_to_e3),
        "E3_provides": ", ".join(e3_provides),
        "sponsor_capacity_level": capacity_level,
        "recommended_ask_level": recommended_ask_level,
        "classification_confidence": confidence,
        "classification_reason": reason,
        "classification_last_updated": timestamp,
    }


def build_email_generation_fields(row: dict) -> dict:
    return {
        "organization_name": _clean_text(row.get("name")) or "Organization",
        "contact_name": _clean_text(row.get("contact_info")),
        "contact_email": _clean_text(row.get("email")),
        "services_to_E3": _clean_text(row.get("services_to_E3")),
        "E3_provides": _clean_text(row.get("E3_provides")),
        "sponsor_capacity_level": _clean_text(row.get("sponsor_capacity_level")) or "Unknown",
        "recommended_ask_level": _clean_text(row.get("recommended_ask_level")) or "Flexible ask",
        "mission_alignment": _clean_text(row.get("giving_priorities")),
        "past_e3_engagement": _clean_text(row.get("past_e3_engagement")),
        "classification_reason": _clean_text(row.get("classification_reason")),
    }
