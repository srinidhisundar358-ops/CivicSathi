DOC_IDS = ["aadhaar", "voter_id", "pan", "driving_licence", "vehicle_rc", "passport",
           "ration_card", "bank_account", "birth_certificate", "pension_ppo"]
SERVICE_IDS = ["aadhaar_address_update", "voter_shift", "dl_address_change", "dl_renewal",
               "vehicle_reregistration", "ration_card_transfer", "passport_reissue",
               "bank_kyc_update", "pension_life_certificate"]
EVENTS = ["relocation_interstate", "relocation_intrastate", "document_expiry", "turning_18"]
STATES = ["karnataka", "maharashtra"]      # plus the pseudo-state "central" for central services
LANGUAGES = ["en", "hi", "kn", "mr"]
FORM_TEMPLATES = ["voter_shift"]
MCP_SERVERS = ["documents", "digilocker", "formfill", "services", "inbox", "deadlines"]
