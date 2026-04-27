from dataclasses import dataclass


@dataclass
class Sponsor:
    name: str
    industry: str | None = None
    description: str | None = None
    goods_and_services: str | None = None
    services_to_e3: str | None = None
    city: str | None = None
    state: str | None = None
    geographical_priorities: str | None = None
    giving_priorities: str | None = None
    past_e3_engagement: str | None = None
    jmu_affiliated: int | None = None
    e3_provides: str | None = None
    website: str | None = None
    contact_info: str | None = None
    sponsor_capacity_level: str | None = None
    recommended_ask_level: str | None = None
    classification_reason: str | None = None


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


def _first_sentence(text: str | None) -> str | None:
    clean = (text or "").strip()
    if not clean:
        return None
    split = clean.split(".")
    first = split[0].strip()
    if not first:
        return None
    return first if first.endswith(".") else f"{first}."


def _org_profile_line(sponsor: Sponsor) -> str:
    goods_services = _first_sentence(sponsor.goods_and_services)
    description = _first_sentence(sponsor.description)
    industry = (sponsor.industry or "").strip()

    if goods_services:
        return f"We appreciate the work {sponsor.name} does through {goods_services.lower()}"
    if description:
        return f"We appreciate the work {sponsor.name} does: {description}"
    if industry:
        return f"We are excited about a potential collaboration with your team in the {industry.lower()} space."
    return "We are excited about a potential collaboration with your team."


def _outreach_alignment_line(sponsor: Sponsor) -> str:
    priorities = _first_sentence(sponsor.giving_priorities)
    geo = _first_sentence(sponsor.geographical_priorities)

    if priorities and geo:
        return (
            f"Your focus on {priorities.lower()} and your geographic priorities in {geo.lower()} "
            "align strongly with Empowerment3's mission."
        )
    if priorities:
        return f"Your focus on {priorities.lower()} aligns strongly with Empowerment3's mission."
    if geo:
        return f"Your geographic priorities in {geo.lower()} align strongly with the communities we serve."
    return "Your organization appears to be mission-aligned with the communities Empowerment3 serves."


def _engagement_line(sponsor: Sponsor) -> str:
    past = _first_sentence(sponsor.past_e3_engagement)
    if past:
        return f"We value your past engagement with Empowerment3: {past}"
    if sponsor.jmu_affiliated == 1:
        return "As a JMU-affiliated organization, you are a natural partner in advancing this work."
    return ""


def _support_request_line(sponsor: Sponsor, email_type: str) -> str:
    services = _first_sentence(sponsor.services_to_e3)
    location = _location_text(sponsor.city, sponsor.state)

    if services:
        return (
            f"We are reaching out to ask whether your organization would be open to supporting "
            f"Empowerment3 through {services.lower()}"
        )

    defaults = {
        "gift_card": (
            "We are reaching out to ask whether your team would consider donating gift cards "
            "for event raffles that support our participants."
        ),
        "partnership_event": (
            "We would love to explore a co-hosted community event where E3 mentors and mentees "
            "can engage with your organization."
        ),
        "partnership_accessibility": (
            "We would love to explore an accessibility-focused partnership where we collaborate "
            "on inclusive programming and community participation."
        ),
        "fundraising": (
            "We are seeking fundraising partners and would value the opportunity to explore a "
            "campaign that supports Empowerment3 participants and families."
        ),
    }
    return f"{defaults[email_type]} We are currently focused on partners in {location}."


def _intro_block() -> str:
    return (
        "I am reaching out on behalf of Empowerment3 (E3), a JMU-connected organization that "
        "provides physical activity and wellness mentorship for children and adults with disabilities, "
        "English language learners, refugees, at-risk youth, veterans, and older adults."
    )


def email_template_gift_card(sponsor: Sponsor) -> str:
    engagement = _engagement_line(sponsor)
    engagement_text = f"\n{engagement}\n" if engagement else "\n"
    return f"""Hello {sponsor.name} team,

{_intro_block()}

{_org_profile_line(sponsor)}
{_outreach_alignment_line(sponsor)}
{engagement_text}
{_support_request_line(sponsor, "gift_card")}

In return, your organization can receive {_benefit_text(sponsor.e3_provides)} through event recognition and community outreach.

Thank you for your consideration. We would be glad to connect at your convenience.

Best,
Empowerment3
"""


def email_template_partnership_event(sponsor: Sponsor) -> str:
    engagement = _engagement_line(sponsor)
    engagement_text = f"\n{engagement}\n" if engagement else "\n"
    return f"""Hello {sponsor.name} team,

{_intro_block()}

{_org_profile_line(sponsor)}
{_outreach_alignment_line(sponsor)}
{engagement_text}
{_support_request_line(sponsor, "partnership_event")}

In return, your organization can receive {_benefit_text(sponsor.e3_provides)} through a visible, mission-aligned community collaboration.

Thank you for your consideration. We would be glad to coordinate details with your team.

Best,
Empowerment3
"""


def email_template_partnership_accessibility(sponsor: Sponsor) -> str:
    engagement = _engagement_line(sponsor)
    engagement_text = f"\n{engagement}\n" if engagement else "\n"
    return f"""Hello {sponsor.name} team,

{_intro_block()}

{_org_profile_line(sponsor)}
{_outreach_alignment_line(sponsor)}
{engagement_text}
{_support_request_line(sponsor, "partnership_accessibility")}

E3 can support your team with practical inclusive programming strategies and a stronger connection to local participants and families.
In return, your organization can receive {_benefit_text(sponsor.e3_provides)} through this collaboration.

Thank you for your consideration. We would welcome a short introductory conversation.

Best,
Empowerment3
"""


def email_template_fundraising(sponsor: Sponsor) -> str:
    engagement = _engagement_line(sponsor)
    engagement_text = f"\n{engagement}\n" if engagement else "\n"
    return f"""Hello {sponsor.name} team,

{_intro_block()}

{_org_profile_line(sponsor)}
{_outreach_alignment_line(sponsor)}
{engagement_text}
{_support_request_line(sponsor, "fundraising")}

In return, your organization can receive {_benefit_text(sponsor.e3_provides)} while helping us expand services for participants across {_location_text(sponsor.city, sponsor.state)}.

Thank you for your consideration. We look forward to the opportunity to partner.

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


