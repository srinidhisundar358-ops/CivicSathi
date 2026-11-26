# MCP tool contracts

Each tool returns a `ToolResult`. The examples use fake demo data. Service facts and verification dates come from the service owner’s verified records.


> **Stub rules for `StubHub` (P1):** use the first Output example of each tool. For `services__get_process` and `documents__get_required_docs`, copy `service_id` / `state` from the call arguments into the example before returning it, so the same example serves every checklist item. The "unknown service" example is what any service_id outside `shared/ids.SERVICE_IDS` must return. The `sources` entry in the `get_process` happy path is a demo placeholder; P3's real data replaces it.

## documents

### `documents__get_affected_documents`

Input

```json
{
  "event": {
    "event_type": "relocation_interstate",
    "from_state": "karnataka",
    "to_state": "maharashtra"
  },
  "held": [
    {
      "doc_id": "aadhaar",
      "origin": "user"
    },
    {
      "doc_id": "voter_id",
      "origin": "user"
    },
    {
      "doc_id": "pan",
      "origin": "user"
    },
    {
      "doc_id": "driving_licence",
      "issued_state": "karnataka",
      "expiry_date": "2027-01-05",
      "origin": "user"
    },
    {
      "doc_id": "vehicle_rc",
      "issued_state": "karnataka",
      "origin": "user"
    }
  ]
}
```

Output

```json
{
  "ok": true,
  "data": [
    {
      "doc_id": "aadhaar",
      "service_id": "aadhaar_address_update",
      "priority": "mandatory",
      "reason": "Other documents use your Aadhaar address as proof, so update it first.",
      "held": true
    },
    {
      "doc_id": "voter_id",
      "service_id": "voter_shift",
      "priority": "mandatory",
      "reason": "You vote where you live, so your voter registration must move to Pune.",
      "held": true
    },
    {
      "doc_id": "driving_licence",
      "service_id": "dl_address_change",
      "priority": "mandatory",
      "reason": "A licence must show your current state address.",
      "held": true
    },
    {
      "doc_id": "vehicle_rc",
      "service_id": "vehicle_reregistration",
      "priority": "mandatory",
      "reason": "A vehicle moving to another state needs re-registration.",
      "held": true
    },
    {
      "doc_id": "bank_account",
      "service_id": "bank_kyc_update",
      "priority": "recommended",
      "reason": "Tell your bank your new address so letters and KYC stay valid.",
      "held": false
    }
  ],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `documents__get_update_order`

Input

```json
{
  "doc_ids": [
    "bank_account",
    "vehicle_rc",
    "driving_licence",
    "voter_id",
    "aadhaar"
  ]
}
```

Output

```json
{
  "ok": true,
  "data": [
    "aadhaar",
    "voter_id",
    "driving_licence",
    "vehicle_rc",
    "bank_account"
  ],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `documents__get_required_docs`

Input

```json
{
  "service_id": "voter_shift",
  "state": "maharashtra"
}
```

Output

```json
{
  "ok": true,
  "data": [
    "aadhaar"
  ],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `documents__get_alternatives`

Input

```json
{
  "doc_id": "aadhaar",
  "purpose": "address_proof"
}
```

Output

```json
{
  "ok": true,
  "data": [],
  "error": null,
  "simulated": false,
  "sources": []
}
```

## digilocker

### `digilocker__start_consent`

Input

```json
{
  "user_id": "demo_ravi"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "id": "demo_request",
    "url": "http://localhost:8000/connect/digilocker/mock-consent?user_id=demo_ravi&request_id=demo_request"
  },
  "error": null,
  "simulated": true,
  "sources": []
}
```

### `digilocker__complete_consent`

Input

```json
{
  "user_id": "demo_ravi",
  "request_id": "demo_request"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "approved": true
  },
  "error": null,
  "simulated": true,
  "sources": []
}
```

### `digilocker__list_documents`

Input

```json
{
  "user_id": "demo_ravi"
}
```

Output

```json
{
  "ok": true,
  "data": [
    {
      "doc_id": "driving_licence",
      "issued_state": "karnataka",
      "expiry_date": "2027-01-05",
      "origin": "digilocker"
    }
  ],
  "error": null,
  "simulated": true,
  "sources": []
}
```

### `digilocker__get_identity_details`

Input

```json
{
  "user_id": "demo_ravi"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "full_name": "Ravi Kumar",
    "address": {
      "line1": "10 Demo Lane",
      "city": "Bengaluru",
      "state": "karnataka",
      "pincode": "560001"
    }
  },
  "error": null,
  "simulated": true,
  "sources": []
}
```

### `digilocker__revoke`

Input

```json
{
  "user_id": "demo_ravi"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "revoked": true
  },
  "error": null,
  "simulated": true,
  "sources": []
}
```

## formfill

### `formfill__list_forms`

Input

```json
{
  "service_id": "voter_shift",
  "state": "maharashtra"
}
```

Output

```json
{
  "ok": true,
  "data": [
    {
      "service_id": "voter_shift",
      "state": "any",
      "form_name": "Voter shift",
      "official_link": "https://voters.eci.gov.in/"
    }
  ],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `formfill__prefill_form`

Input

```json
{
  "service_id": "voter_shift",
  "state": "maharashtra",
  "profile": {
    "user_id": "demo_ravi",
    "language": "en",
    "age": 29,
    "birth_state": "karnataka",
    "current_state": "karnataka",
    "personal": {
      "full_name": "Ravi Kumar",
      "address": {
        "line1": "10 Demo Lane",
        "city": "Bengaluru",
        "state": "karnataka",
        "pincode": "560001"
      }
    },
    "documents": [
      {
        "doc_id": "aadhaar",
        "origin": "user"
      },
      {
        "doc_id": "voter_id",
        "origin": "user"
      },
      {
        "doc_id": "pan",
        "origin": "user"
      },
      {
        "doc_id": "driving_licence",
        "issued_state": "karnataka",
        "expiry_date": "2027-01-05",
        "origin": "user"
      },
      {
        "doc_id": "vehicle_rc",
        "issued_state": "karnataka",
        "origin": "user"
      }
    ],
    "consents": {
      "sms": true,
      "gmail": false,
      "digilocker": false
    }
  }
}
```

Output

```json
{
  "ok": true,
  "data": {
    "form_id": "demo_voter_shift",
    "user_id": "demo_ravi",
    "service_id": "voter_shift",
    "state": "maharashtra",
    "fields": [
      {
        "field_id": "full_name",
        "label": "Full name",
        "value": "Ravi Kumar",
        "source": "profile",
        "required": true,
        "needs_user_input": false
      },
      {
        "field_id": "epic_number",
        "label": "EPIC number",
        "source": "user",
        "required": true,
        "needs_user_input": true
      }
    ],
    "missing": [
      "epic_number"
    ],
    "official_link": "https://voters.eci.gov.in/",
    "status": "draft"
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `formfill__list_missing_fields`

Input

```json
{
  "form": {
    "form_id": "demo_voter_shift",
    "user_id": "demo_ravi",
    "service_id": "voter_shift",
    "state": "maharashtra",
    "fields": [
      {
        "field_id": "full_name",
        "label": "Full name",
        "value": "Ravi Kumar",
        "source": "profile",
        "required": true,
        "needs_user_input": false
      },
      {
        "field_id": "epic_number",
        "label": "EPIC number",
        "source": "user",
        "required": true,
        "needs_user_input": true
      }
    ],
    "missing": [
      "epic_number"
    ],
    "official_link": "https://voters.eci.gov.in/",
    "status": "draft"
  }
}
```

Output

```json
{
  "ok": true,
  "data": [
    "epic_number"
  ],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `formfill__render_form_pdf`

Input

```json
{
  "form": {
    "form_id": "demo_voter_shift",
    "user_id": "demo_ravi",
    "service_id": "voter_shift",
    "state": "maharashtra",
    "fields": [
      {
        "field_id": "full_name",
        "label": "Full name",
        "value": "Ravi Kumar",
        "source": "profile",
        "required": true,
        "needs_user_input": false
      },
      {
        "field_id": "epic_number",
        "label": "EPIC number",
        "source": "user",
        "required": true,
        "needs_user_input": true
      }
    ],
    "missing": [
      "epic_number"
    ],
    "official_link": "https://voters.eci.gov.in/",
    "status": "draft"
  }
}
```

Output

```json
{
  "ok": true,
  "data": {
    "pdf_path": "./generated/demo_voter_shift.pdf",
    "file_name": "demo_voter_shift.pdf"
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```

## services

### `services__get_process`

Input

```json
{
  "service_id": "voter_shift",
  "state": "maharashtra"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "service_id": "voter_shift",
    "state": "maharashtra",
    "authority": "Election Commission of India",
    "official_link": "https://voters.eci.gov.in/",
    "steps": [
      "Sign in to the Voters' Service Portal with your own account.",
      "Choose the option for shifting your residence (Form 8).",
      "Enter your new address in Pune and your EPIC number yourself.",
      "Review everything, then submit it yourself on the portal."
    ],
    "fee": null,
    "required_docs": [
      "aadhaar"
    ],
    "processing_time": null,
    "verified": false
  },
  "error": null,
  "simulated": true,
  "sources": []
  
}
```

Output - example 2: unknown service (safety demo, never guess)

```json
{
  "ok": true,
  "data": {
    "service_id": "driving_abroad_permit",
    "state": "maharashtra",
    "authority": null,
    "official_link": null,
    "steps": [],
    "fee": null,
    "required_docs": [],
    "processing_time": null,
    "verified": false
  },
  "error": "unverified: not in our official data",
  "simulated": false,
  "sources": []
}
```

### `services__get_authority`

Input

```json
{
  "service_id": "voter_shift",
  "state": "maharashtra"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "authority": null,
    "portal_name": null,
    "official_link": null
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `services__explain_term`

Input

```json
{
  "term": "EPIC",
  "language": "en"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "term": "EPIC",
    "language": "en",
    "explanation": "Elector Photo Identity Card"
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```

## inbox

### `inbox__extract_from_message`

Input

```json
{
  "message": {
    "message_id": "demo_dl_sms",
    "user_id": "demo_ravi",
    "channel": "sms",
    "sender": "DEMO-DL",
    "text": "Demo: your driving licence expires 05 Jan 2027.",
    "received_at": "2026-11-26T12:00:00+05:30"
  }
}
```

Output

```json
{
  "ok": true,
  "data": {
    "message_id": "demo_dl_sms",
    "is_government": true,
    "category": "deadline",
    "doc_id": "driving_licence",
    "service_id": "dl_renewal",
    "due_date": "2027-01-05",
    "summary": "Driving licence expires on 5 Jan 2027",
    "confidence": 1.0
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `inbox__is_government_sender`

Input

```json
{
  "sender": "DEMO-DL",
  "channel": "sms"
}
```

Output

```json
{
  "ok": true,
  "data": true,
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `inbox__start_gmail_consent`

Input

```json
{
  "user_id": "demo_ravi"
}
```

Output

```json
{
  "ok": false,
  "data": null,
  "error": "Gmail OAuth is disabled for this prototype",
  "simulated": true,
  "sources": []
}
```

### `inbox__complete_gmail_consent`

Input

```json
{
  "user_id": "demo_ravi",
  "code": "demo_code"
}
```

Output

```json
{
  "ok": false,
  "data": null,
  "error": "Gmail OAuth is disabled for this prototype",
  "simulated": true,
  "sources": []
}
```

### `inbox__fetch_recent_emails`

Input

```json
{
  "user_id": "demo_ravi",
  "since_hours": 24
}
```

Output

```json
{
  "ok": true,
  "data": [
    {
      "message_id": "demo_dl_email",
      "user_id": "demo_ravi",
      "channel": "email",
      "sender": "notices@example.org",
      "text": "Demo: your driving licence expires 05 Jan 2027.",
      "received_at": "2026-11-26T12:00:00+05:30"
    }
  ],
  "error": null,
  "simulated": true,
  "sources": []
}
```

## deadlines

### `deadlines__add_reminder`

Input

```json
{
  "reminder": {
    "reminder_id": "demo_dl_reminder",
    "user_id": "demo_ravi",
    "doc_id": "driving_licence",
    "title": "Driving licence expiry",
    "due_date": "2027-01-05",
    "channel": "app",
    "source_message_id": "demo_dl_sms"
  }
}
```

Output

```json
{
  "ok": true,
  "data": {
    "reminder_id": "demo_dl_reminder",
    "user_id": "demo_ravi",
    "doc_id": "driving_licence",
    "title": "Driving licence expiry",
    "due_date": "2027-01-05",
    "channel": "app",
    "source_message_id": "demo_dl_sms"
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `deadlines__list_upcoming`

Input

```json
{
  "user_id": "demo_ravi",
  "days": 7
}
```

Output

```json
{
  "ok": true,
  "data": [],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `deadlines__check_overdue`

Input

```json
{
  "user_id": "demo_ravi"
}
```

Output

```json
{
  "ok": true,
  "data": [],
  "error": null,
  "simulated": false,
  "sources": []
}
```

### `deadlines__get_renewal_rule`

Input

```json
{
  "doc_id": "driving_licence"
}
```

Output

```json
{
  "ok": true,
  "data": {
    "doc_id": "driving_licence",
    "validity": null,
    "renew_before_days": null,
    "official_link": null
  },
  "error": null,
  "simulated": false,
  "sources": []
}
```
