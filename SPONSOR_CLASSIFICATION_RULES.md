# Sponsor Classification Rules (Empowerment3)

## Purpose
This rules-based system classifies each sponsor row in the Empowerment3 database to produce consistent, explainable recommendations for outreach and email preparation.

The system recommends:
- what a sponsor can provide to E3
- what E3 can provide back
- sponsor capacity level
- recommended ask level
- confidence score
- classification reason
- email-generation support fields

## Rule Safety
- The system must **not invent information**.
- It only uses data already present in each sponsor row.
- If row data is insufficient, values should remain conservative (`Unknown` or `Flexible ask`).
- Rules-based logic is the default; AI can assist only for unclear edge cases or email drafting.

## Fields Used and Created
Classification-related fields supported in the database:
- `services_to_E3`
- `E3_provides`
- `sponsor_capacity_level`
- `recommended_ask_level`
- `classification_confidence`
- `classification_reason`
- `classification_last_updated`
- `manual_override`

## services_to_E3 Definitions
Possible values:
- `gift card / donation of goods/service`
- `monetary donation`
- `partnership, one-time or ongoing`
- `Flexible ask` (fallback when row data is insufficient)

Rules are keyword and row-attribute driven (industry/description/type/location context), and may assign multiple values when multiple rules match.

## E3_provides Definitions
Possible values:
- `visibility`
- `more inclusive / accessible`
- `helping out the community`
- `Unknown` (fallback when row data is insufficient)

Rules can assign multiple values where appropriate.

## Sponsor Capacity Rules
Allowed values:
- `High`
- `Medium`
- `Low`
- `Unknown`

Guiding logic:
- `High`: dealership/bank/health system/resort/university/major institution/regional-national or formal-giving indicators.
- `Medium`: established local restaurants, beverage businesses, gyms/sports/recreation, event/hospitality, stable local service businesses.
- `Low`: small shops/vendors/boutiques/student groups/small nonprofits/small craft businesses.
- `Unknown`: insufficient row evidence.

## Recommended Ask Level Rules
Direct mapping:
- `High` -> `Large ask`
- `Medium` -> `Moderate ask`
- `Low` -> `Small ask`
- `Unknown` -> `Flexible ask`

## Confidence Score Definitions
Allowed values:
- `High confidence`
- `Medium confidence`
- `Low confidence`
- `Unknown confidence`

Interpretation:
- `High confidence`: multiple concrete fields support rule matches.
- `Medium confidence`: partial data supports likely classification.
- `Low confidence`: limited data with weak but reasonable rule signal.
- `Unknown confidence`: insufficient data to classify capacity.

## Manual Override Behavior
- If `manual_override = 1`, rule recalculation is skipped for that row.
- If `manual_override = 0` (or blank/false), row can be classified/reclassified.
- Existing values are preserved unless user explicitly chooses recalculation.

## Email Generation Logic Support
Prepared email context fields include:
- organization name
- contact name (if available; never invented)
- contact email (if available)
- `services_to_E3`
- `E3_provides`
- `sponsor_capacity_level`
- `recommended_ask_level`
- mission alignment (from existing row fields, if present)
- `past_e3_engagement` (only if present; never invented)
- `classification_reason`

Ask strategy alignment:
- High capacity -> larger sponsorship/monetary ask
- Medium capacity -> moderate gift card/goods/services/partnership ask
- Low capacity -> small gift card/product/raffle/one-time ask
- Unknown capacity -> flexible ask

## Example Outcomes
### Example 1
Sponsor: Steven Toyota  
Likely capacity: High  
services_to_E3: monetary donation, gift card / donation of goods/service, partnership  
E3_provides: visibility, helping out the community  
recommended_ask_level: Large ask  
Reason: Car dealership with stronger likely sponsorship capacity than a small local business.

### Example 2
Sponsor: local coffee shop  
Likely capacity: Low  
services_to_E3: gift card / donation of goods/service  
E3_provides: visibility, helping out the community  
recommended_ask_level: Small ask  
Reason: Small business likely better suited for a small gift card, product donation, or raffle item.

### Example 3
Sponsor: Brothers Craft Brewing  
Likely capacity: Medium  
services_to_E3: gift card / donation of goods/service, partnership  
E3_provides: visibility, helping out the community  
recommended_ask_level: Moderate ask  
Reason: Established local food/beverage business that could donate goods/services and benefit from community visibility.

### Example 4
Sponsor: Massanutten Resort  
Likely capacity: High  
services_to_E3: gift card / donation of goods/service, monetary donation, partnership  
E3_provides: visibility, more inclusive / accessible, helping out the community  
recommended_ask_level: Large ask  
Reason: Large recreation/hospitality organization with potential for experiences, sponsorship, and accessibility/community partnership.

## Maintainability Note
The rule sets are centralized in `classification_logic.py` so keywords and mappings can be edited later without changing app flow.
