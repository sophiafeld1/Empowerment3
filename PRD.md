# 1. Goal: To create a database and simple UI for Empowerment3 to be able to query sponsor data easily. 

# About E3:
mission: We seek to empower individuals and their families, professionals (in-service and pre-service), and communities, using through physical activity and wellness, mentorship, career readiness, and social connection.  
what they do: Weekly physical activity & nutrition mentorship interventionson campus or int he community to improve physical health, emotional wellness, career readiness, and quality of life outcomes.
E3 serves 300 children and adults with disabilities, English language learners, refugees, at-risk youth, veterans, and older adults (ages 2-100) annually.

# Schema:

`Name`: business name (str)
`industry`: type of business what is their industry (str) restaurant, retail, fitness, healthcare, nonprofit, student org, etc.)
`description`: about the business / org (str)
`services_to_E3`: What the business can provide to E3 (multi-select): gift card, parternship-event, partnership-accessibility, fundrasing
`organization_type`:(business, nonprofit, club/org, school unit)
`E3_provides`: What does E3 provide to them? (multi-select): visibility, accessibility consulting services, helping their community (str)
`email`: contact info email (str)
`phone`: ###-###-#### (str)
`city`: (str)
`state`: (str)
`zip`: (int)
`website`: (str)
`company_size`: (int)
`has_physical_location`: (bool)
`location_accessibility_level`: (unknown/basic/advanced) (str) unknown = no reliable info, basic = wheelchair access / ADA basics visible, advanced = clear accessibility features beyond basics, detailed info provided
`has_community_giving_program`: (bool)
`serves_populations`:(disability community, youth, refugees, veterans, older adults) (multi-select)
`jmu_affiliated`: bool
`past_e3_engagement`: (str) none/contacted/partnered/donated 
`collaborates_with_community` low, medium, high low = little visible, community involvement, medium = some partnerships/sponsorships/community activity, high = frequent, public, ongoing community engagement



# email templates:
templates will include feilds to replace with information about the company to request their services. It will include both services to E3 and E3 provides.

Catagories:
**1. gift card:** ask business if they would be willing to donate (a) gift card(s) to E3 in exchange for their name on the event flier. Giftcards could be used for raffles during events.

**2. partnership-event:** ask business if they would like to partner for an event together (E3's mentors and mentees or veterans).

**3.partnership-accesibility:** ask business if they would like E3 to partner for an event together that is accesible for E3 mentees and includes E3 teaching the business how to serve individuals with disabilities. 

**4.fundraising:** ask business if they would like to fundraise for E3. This mainly applies to organizations/clubs at JMU as they fundraise for phillanthopy.

**Catagories of the benefit businesses would receive in exchange:**
1. visibility of their busines (feature on instagram, feature on flier, bringing E3 mentors and mentees to their business)
2. accesibility consulting services (activities accesible for individuals with disabilities)
3. helping the community (phillanthropic reasons)

# Data Collection + Verification (Brief)
- Use a hybrid approach: web research + LLM extraction + manual review for high-priority records.
- Source order: business website, contact/about pages, Google profile, LinkedIn, student org directories.
- Store `source_url` and `confidence_score` (0-100) for each record.
- Verification status: `unverified`, `partially_verified`, `verified`.

## Minimum manual check (before outreach)
- Confirm business name, website, and location.
- Confirm at least one working contact method (prefer email).
- Confirm top calculated match for `services_to_E3`.
- Confirm `E3_provides` value in the email template matches business type.

## Confidence policy
- `80-100`: trusted for auto-categorization and draft email generation.
- `60-79`: include in database, but require manual review before sending outreach.
- `<60`: keep as lead only; do not use for outreach until verified.
