# CivicSaathi - Person 3: Services and Inbox

## Responsibilities

- Government services knowledge base.
- Government SMS and email sender filtering.
- Deadline, payment and application status extraction.
- OTP detection and removal.
- Simulated Gmail integration.
- Synthetic test messages.

## Official Government Source Portals

### Central Services

- UIDAI: https://uidai.gov.in/
- MyAadhaar: https://myaadhaar.uidai.gov.in/
- Election Commission: https://eci.gov.in/
- Voters Portal: https://voters.eci.gov.in/
- Passport Seva: https://www.passportindia.gov.in/
- Jeevan Pramaan: https://jeevanpramaan.gov.in/
- RBI: https://www.rbi.org.in/
- National Food Security Portal: https://nfsa.gov.in/

### Karnataka Services

- Karnataka Transport: https://transport.karnataka.gov.in/
- Sarathi: https://sarathi.parivahan.gov.in/
- Vahan: https://vahan.parivahan.gov.in/
- Parivahan: https://parivahan.gov.in/

### Maharashtra Services

- Maharashtra Transport: https://transport.maharashtra.gov.in/
- Sarathi: https://sarathi.parivahan.gov.in/
- Vahan: https://vahan.parivahan.gov.in/

## Data Verification Rules

- Use official government sources only.
- Never invent fees or processing times.
- Unconfirmed values remain null.
- Unknown services must return unverified.
- Record verification dates only for pages actually checked.

## Privacy Rules

- Detect and discard OTP content before further extraction.
- Never log or return raw message text.
- Use synthetic messages for testing.
- Gmail integration is simulated for the prototype.
- Sender matching does not guarantee message authenticity.

## MCP Servers

- Services MCP: Port 8201
- Inbox MCP: Port 8202

## Demo Users

- demo_ravi: Driving licence expires on 2027-01-05.
- demo_ajji: Pension life certificate due on 2026-11-30.

## Testing Targets

- 18 synthetic test messages.
- At least 90% category extraction accuracy.
- All OTP messages safely dropped.
- Correct document, service and deadline for both demo users.
- Unknown services returned as unverified.

## TODO-verify

- Complete passport and pension service data.
- Verify exact government source URLs and verification dates.
- Consolidate all individual source URLs from service JSON files.
- Confirm required documents, fees and processing times.
- Check state-specific ration card procedures.
- Collect actual SMS sender headers from team phones.
- Check whether government SMS headers end in -G.
- Add the team's demo SMS number.
- Review Hindi and Kannada glossary translations.
- Test both MCP servers and shared contract compatibility.
- Run extraction accuracy tests in mock mode.
