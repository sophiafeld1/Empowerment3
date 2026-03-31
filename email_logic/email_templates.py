from dataclasses import dataclass


@dataclass
class Sponsor:
    name: str
    industry: str | None = None
    city: str | None = None
    state: str | None = None
    e3_provides: str | None = None


EMAIL_TYPES = [
    "gift_card",
    "partnership_event",
    "partnership_accessibility",
    "fundraising",
]


def _location_text(city: str | None, state: str | None) -> str:
    city = (city or "").strip()
    state = (state or "").strip()
    if city and state:
        return f"{city}, {state}"
    if city:
        return city
    if state:
        return state
    return "our community"


def _benefit_text(e3_provides: str | None) -> str:
    clean = (e3_provides or "").strip()
    if clean:
        return clean
    return "community visibility, mission-aligned partnership opportunities, and local impact"


def email_template_gift_card(sponsor: Sponsor) -> str:
    return f"""Hi {sponsor.name},

We are Empowerment3, a JMU-run organization that provides physical activity and wellness mentorship to children and adults with disabilities, English language learners, refugees, at-risk youth, veterans, and older adults.

We are currently looking for local partners in {_location_text(sponsor.city, sponsor.state)}. We would love to ask whether your team would consider donating gift card(s) for event raffles that support our participants.

In return, your business can receive {_benefit_text(sponsor.e3_provides)} through event recognition and community outreach.

Thank you for your consideration.
Best,
Empowerment3
"""


def email_template_partnership_event(sponsor: Sponsor) -> str:
    return f"""Hi {sponsor.name},

We are Empowerment3, a JMU-run organization that provides physical activity and wellness mentorship to children and adults with disabilities, English language learners, refugees, at-risk youth, veterans, and older adults.

We would love to explore a partnership event with your organization in {_location_text(sponsor.city, sponsor.state)}. This could include a collaborative activity where E3 mentors and mentees engage with your business and community.

In return, your business can receive {_benefit_text(sponsor.e3_provides)}.

Thank you for your consideration.
Best,
Empowerment3
"""


def email_template_partnership_accessibility(sponsor: Sponsor) -> str:
    return f"""Hi {sponsor.name},

We are Empowerment3, an organization that provides physical activity and wellness mentorship to children and adults with disabilities, English language learners, refugees, at-risk youth, veterans, and older adults.

We are reaching out to explore an accessibility-focused partnership in {_location_text(sponsor.city, sponsor.state)}. E3 can support your team with inclusive activity planning and practical strategies for serving individuals with disabilities.

In return, your organization can receive {_benefit_text(sponsor.e3_provides)} through this collaboration.

Thank you for your consideration.
Best,
Empowerment3
"""


def email_template_fundraising(sponsor: Sponsor) -> str:
    return f"""Hi {sponsor.name},

We are Empowerment3, an organization that provides physical activity and wellness mentorship to children and adults with disabilities, English language learners, refugees, at-risk youth, veterans, and older adults.

We are currently seeking fundraising partners in {_location_text(sponsor.city, sponsor.state)} and would love to explore whether your organization would be interested in supporting E3 through a fundraiser.

In return, your organization can receive {_benefit_text(sponsor.e3_provides)} while helping us expand services for our participants.

Thank you for your consideration.
Best,
Empowerment3
"""


def generate_email_draft(sponsor: Sponsor, email_type: str) -> str:
    email_type = (email_type or "").strip().lower()
    templates = {
        "gift_card": email_template_gift_card,
        "partnership_event": email_template_partnership_event,
        "partnership_accessibility": email_template_partnership_accessibility,
        "fundraising": email_template_fundraising,
    }

    if email_type not in templates:
        raise ValueError(f"Unsupported email_type: {email_type}")

    return templates[email_type](sponsor)