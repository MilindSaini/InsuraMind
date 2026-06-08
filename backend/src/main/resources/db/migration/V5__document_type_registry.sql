-- ============================================================================
-- V5: Document Type Registry (DTR)
--
-- One row per document type. Every pipeline stage reads its config from here.
-- Adding a new document type = inserting a new row, not writing code.
-- ============================================================================

SET search_path TO insuramind;

CREATE TABLE document_type_registry (
    doc_type            VARCHAR(64)  PRIMARY KEY,
    display_name        VARCHAR(128) NOT NULL,
    entity_schema       JSONB        NOT NULL DEFAULT '{}',
    section_taxonomy    JSONB        NOT NULL DEFAULT '{}',
    query_intents       JSONB        NOT NULL DEFAULT '[]',
    risk_patterns       JSONB        NOT NULL DEFAULT '[]',
    answer_templates    JSONB        NOT NULL DEFAULT '{}',
    regulatory_context  TEXT         NOT NULL DEFAULT '',
    classifier_exemplar TEXT         NOT NULL DEFAULT '',
    classifier_terms    JSONB        NOT NULL DEFAULT '[]',
    enabled             BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dtr_enabled ON document_type_registry(enabled) WHERE enabled = TRUE;

-- Soft index on documents.document_type for DTR joins
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(document_type);

-- ============================================================================
-- Seed: insurance_policy
-- ============================================================================
INSERT INTO document_type_registry (doc_type, display_name, entity_schema, section_taxonomy,
    query_intents, risk_patterns, answer_templates, regulatory_context,
    classifier_exemplar, classifier_terms)
VALUES (
    'insurance_policy',
    'Insurance Policy',
    '{
        "policy_number":    {"type": "text"},
        "sum_insured":      {"type": "monetary"},
        "premium":          {"type": "monetary"},
        "copay":            {"type": "percentage"},
        "deductible":       {"type": "monetary"},
        "waiting_period":   {"type": "duration"},
        "room_rent_limit":  {"type": "monetary"},
        "insurer_name":     {"type": "text"},
        "hospital":         {"type": "text"}
    }'::jsonb,
    '{
        "coverage":       ["Coverage", "Benefit", "Sum Insured", "Room Rent", "Cashless"],
        "exclusion":      ["Exclusion", "Not Covered", "Excluded", "Limitations", "Permanent Exclusion"],
        "waiting_period": ["Waiting Period", "Pre-existing", "PED", "Survival Period"],
        "claim_rule":     ["Claim", "Documents Required", "Intimation", "Settlement", "Deductible", "Co-pay"],
        "definition":     ["Definition", "Means", "Interpretation"],
        "renewal":        ["Renewal", "Cancellation", "Termination", "Grace Period"]
    }'::jsonb,
    '["coverage_check", "exclusion_check", "claim_process_check", "waiting_period_check", "premium_check", "network_hospital_check"]'::jsonb,
    '["hidden_exclusion", "low_sum_insured", "high_copay", "short_free_look", "sub_limit_trap", "no_restoration_benefit"]'::jsonb,
    '{
        "coverage_check": {
            "fields": ["sum_insured", "room_rent_limit", "copay", "deductible"],
            "verdict_format": "Your sum insured is ₹{sum_insured}. Room rent limit: {room_rent_limit}. Co-pay: {copay}. Deductible: ₹{deductible}."
        },
        "exclusion_check": {
            "fields": ["exclusion_list", "waiting_period"],
            "verdict_format": "Key exclusions found: {exclusion_list}. Waiting period for pre-existing diseases: {waiting_period}."
        },
        "claim_process_check": {
            "fields": ["claim_intimation_period", "documents_required"],
            "verdict_format": "Claim must be intimated within {claim_intimation_period}. Required documents: {documents_required}."
        }
    }'::jsonb,
    'IRDAI regulations, Insurance Act 1938, IRDAI (Health Insurance) Regulations',
    'insurance policy schedule sum insured premium exclusions waiting period coverage benefits room rent deductible co-pay renewal terms policy number',
    '["policy number", "sum insured", "premium", "exclusions", "waiting period", "co-pay", "copay", "deductible", "room rent"]'::jsonb
);

-- ============================================================================
-- Seed: loan_agreement
-- ============================================================================
INSERT INTO document_type_registry (doc_type, display_name, entity_schema, section_taxonomy,
    query_intents, risk_patterns, answer_templates, regulatory_context,
    classifier_exemplar, classifier_terms)
VALUES (
    'loan_agreement',
    'Loan Agreement',
    '{
        "principal":            {"type": "monetary"},
        "interest_rate":        {"type": "percentage"},
        "emi":                  {"type": "monetary"},
        "tenure":               {"type": "duration"},
        "prepayment_penalty":   {"type": "percentage"},
        "collateral":           {"type": "asset"},
        "processing_fee":       {"type": "monetary"},
        "late_payment_charge":  {"type": "percentage"},
        "loan_account_number":  {"type": "text"},
        "borrower_name":        {"type": "text"},
        "lender_name":          {"type": "text"}
    }'::jsonb,
    '{
        "terms":     ["Loan Terms", "Principal Amount", "Interest Rate", "Rate of Interest"],
        "repayment": ["EMI Schedule", "Repayment", "Instalment", "Payment Schedule"],
        "default":   ["Events of Default", "Default", "Non-Payment", "Acceleration"],
        "security":  ["Collateral", "Mortgage", "Security Interest", "Hypothecation", "Pledge"],
        "fees":      ["Processing Fee", "Charges", "Fees", "Stamp Duty"],
        "prepayment":["Prepayment", "Foreclosure", "Part Payment", "Early Repayment"]
    }'::jsonb,
    '["repayment_check", "prepayment_penalty_check", "default_consequence_check", "collateral_check", "interest_rate_check", "fee_check"]'::jsonb,
    '["floating_rate_unilateral_change", "cross_default_clause", "hidden_processing_fee", "excessive_late_fee", "no_prepayment_option", "blanket_lien"]'::jsonb,
    '{
        "repayment_check": {
            "fields": ["emi", "tenure", "total_interest", "rate_type"],
            "verdict_format": "Your EMI is ₹{emi} for {tenure} months. Total interest = ₹{total_interest}. Rate type: {rate_type}."
        },
        "prepayment_penalty_check": {
            "fields": ["prepayment_penalty", "lock_in_period", "conditions"],
            "verdict_format": "Prepayment penalty: {prepayment_penalty}. Lock-in period: {lock_in_period}. {conditions}"
        },
        "default_consequence_check": {
            "fields": ["default_triggers", "consequences", "cure_period"],
            "verdict_format": "Default triggers: {default_triggers}. Consequences: {consequences}. Cure period: {cure_period}."
        }
    }'::jsonb,
    'RBI lending norms, FEMA guidelines, NHB regulations for home loans, RBI Fair Practices Code',
    'loan agreement principal amount interest rate emi equated monthly instalment tenure repayment prepayment penalty collateral mortgage security borrower lender',
    '["loan", "principal", "interest rate", "emi", "equated monthly", "mortgage", "collateral", "borrower", "lender", "repayment"]'::jsonb
);

-- ============================================================================
-- Seed: kyc_document
-- ============================================================================
INSERT INTO document_type_registry (doc_type, display_name, entity_schema, section_taxonomy,
    query_intents, risk_patterns, answer_templates, regulatory_context,
    classifier_exemplar, classifier_terms)
VALUES (
    'kyc_document',
    'KYC Document',
    '{
        "document_number":  {"type": "text"},
        "full_name":        {"type": "text"},
        "date_of_birth":    {"type": "date"},
        "address":          {"type": "text"},
        "expiry_date":      {"type": "date"},
        "issue_date":       {"type": "date"},
        "issuing_authority": {"type": "text"},
        "document_class":   {"type": "text"}
    }'::jsonb,
    '{
        "identity":  ["Identity", "Name", "Photo", "Photograph"],
        "address":   ["Address", "Residence", "Permanent Address", "Correspondence"],
        "validity":  ["Valid", "Expiry", "Issue Date", "Validity Period"],
        "authority": ["Issued By", "Government of India", "Authority"]
    }'::jsonb,
    '["validity_check", "expiry_check", "address_match_check", "identity_verify_check"]'::jsonb,
    '["expired_document", "mismatched_name", "address_discrepancy", "tampered_document", "missing_photo"]'::jsonb,
    '{
        "validity_check": {
            "fields": ["document_number", "issue_date", "expiry_date", "status"],
            "verdict_format": "Document {document_number} issued on {issue_date}. Expiry: {expiry_date}. Status: {status}."
        },
        "expiry_check": {
            "fields": ["expiry_date", "days_remaining"],
            "verdict_format": "Document expires on {expiry_date}. {days_remaining} days remaining."
        }
    }'::jsonb,
    'RBI KYC Master Direction, PMLA 2002, SEBI KYC norms, UIDAI Aadhaar guidelines',
    'aadhaar pan card identity proof address proof kyc date of birth government identification number passport voter id driving licence',
    '["aadhaar", "pan card", "kyc", "identity proof", "address proof", "passport", "voter id", "driving licence"]'::jsonb
);

-- ============================================================================
-- Seed: legal_contract
-- ============================================================================
INSERT INTO document_type_registry (doc_type, display_name, entity_schema, section_taxonomy,
    query_intents, risk_patterns, answer_templates, regulatory_context,
    classifier_exemplar, classifier_terms)
VALUES (
    'legal_contract',
    'Legal Contract',
    '{
        "parties":              {"type": "text"},
        "effective_date":       {"type": "date"},
        "termination_clause":   {"type": "text"},
        "liability_cap":        {"type": "monetary"},
        "jurisdiction":         {"type": "text"},
        "governing_law":        {"type": "text"},
        "indemnification":      {"type": "text"},
        "confidentiality_term": {"type": "duration"},
        "notice_period":        {"type": "duration"}
    }'::jsonb,
    '{
        "parties":       ["Parties", "Between", "Party A", "Party B", "First Party", "Second Party"],
        "obligations":   ["Obligations", "Duties", "Responsibilities", "Covenants", "Undertakings"],
        "liability":     ["Liability", "Indemnification", "Indemnity", "Damages", "Limitation of Liability"],
        "termination":   ["Termination", "Expiry", "Cancellation", "Exit", "Break Clause"],
        "confidential":  ["Confidentiality", "Non-Disclosure", "NDA", "Trade Secret"],
        "dispute":       ["Dispute Resolution", "Arbitration", "Jurisdiction", "Governing Law"],
        "general":       ["Miscellaneous", "General Provisions", "Force Majeure", "Severability"]
    }'::jsonb,
    '["obligation_check", "liability_check", "termination_check", "jurisdiction_check", "confidentiality_check", "indemnification_check"]'::jsonb,
    '["unlimited_liability", "unilateral_termination", "unfavorable_jurisdiction", "one_sided_indemnity", "no_force_majeure", "auto_renewal_trap", "non_compete_overreach"]'::jsonb,
    '{
        "obligation_check": {
            "fields": ["party_obligations", "deadlines", "penalties"],
            "verdict_format": "Key obligations: {party_obligations}. Deadlines: {deadlines}. Non-compliance penalties: {penalties}."
        },
        "liability_check": {
            "fields": ["liability_cap", "indemnification_scope", "exclusions"],
            "verdict_format": "Liability cap: {liability_cap}. Indemnification covers: {indemnification_scope}. Excluded: {exclusions}."
        },
        "termination_check": {
            "fields": ["termination_triggers", "notice_period", "consequences"],
            "verdict_format": "Termination triggers: {termination_triggers}. Notice period: {notice_period}. Post-termination: {consequences}."
        }
    }'::jsonb,
    'Indian Contract Act 1872, Specific Relief Act, Arbitration and Conciliation Act 1996',
    'agreement contract between parties hereby agrees obligations liability indemnification termination governing law jurisdiction arbitration confidentiality',
    '["agreement", "contract", "hereby", "parties", "obligations", "indemnification", "termination", "jurisdiction", "arbitration", "governing law"]'::jsonb
);

-- ============================================================================
-- Seed: bond_instrument
-- ============================================================================
INSERT INTO document_type_registry (doc_type, display_name, entity_schema, section_taxonomy,
    query_intents, risk_patterns, answer_templates, regulatory_context,
    classifier_exemplar, classifier_terms)
VALUES (
    'bond_instrument',
    'Bond / Debenture',
    '{
        "face_value":       {"type": "monetary"},
        "coupon_rate":      {"type": "percentage"},
        "maturity_date":    {"type": "date"},
        "yield_to_maturity":{"type": "percentage"},
        "credit_rating":    {"type": "text"},
        "issuer":           {"type": "text"},
        "trustee":          {"type": "text"},
        "isin":             {"type": "text"},
        "call_date":        {"type": "date"},
        "put_date":         {"type": "date"}
    }'::jsonb,
    '{
        "terms":      ["Terms of Issue", "Face Value", "Coupon", "Interest Payment"],
        "covenants":  ["Covenants", "Restrictive Covenants", "Affirmative Covenants", "Financial Covenants"],
        "redemption": ["Redemption", "Maturity", "Call Option", "Put Option", "Buyback"],
        "security":   ["Security", "Secured", "Unsecured", "Charge", "Debenture Trust Deed"],
        "default":    ["Events of Default", "Cross Default", "Acceleration"],
        "rating":     ["Credit Rating", "Rating", "CRISIL", "ICRA", "CARE"]
    }'::jsonb,
    '["covenant_check", "redemption_check", "rating_change_check", "yield_check", "default_risk_check", "security_check"]'::jsonb,
    '["covenant_breach_risk", "call_risk", "credit_downgrade", "subordination_risk", "no_put_option", "cross_default_trigger"]'::jsonb,
    '{
        "covenant_check": {
            "fields": ["covenants_list", "financial_ratios", "compliance_status"],
            "verdict_format": "Key covenants: {covenants_list}. Financial ratio requirements: {financial_ratios}. Compliance: {compliance_status}."
        },
        "redemption_check": {
            "fields": ["maturity_date", "call_date", "put_date", "redemption_premium"],
            "verdict_format": "Maturity: {maturity_date}. Call option: {call_date}. Put option: {put_date}. Redemption premium: {redemption_premium}."
        },
        "yield_check": {
            "fields": ["coupon_rate", "yield_to_maturity", "credit_rating"],
            "verdict_format": "Coupon: {coupon_rate}. YTM: {yield_to_maturity}. Credit rating: {credit_rating}."
        }
    }'::jsonb,
    'SEBI (Issue and Listing of Non-Convertible Securities) Regulations 2021, RBI guidelines on corporate bonds, SEBI LODR',
    'bond debenture face value coupon rate maturity yield credit rating issuer trustee isin call put redemption covenant',
    '["bond", "debenture", "coupon", "maturity", "yield", "credit rating", "isin", "trustee", "face value", "redemption"]'::jsonb
);

-- ============================================================================
-- Seed: term_sheet
-- ============================================================================
INSERT INTO document_type_registry (doc_type, display_name, entity_schema, section_taxonomy,
    query_intents, risk_patterns, answer_templates, regulatory_context,
    classifier_exemplar, classifier_terms)
VALUES (
    'term_sheet',
    'Term Sheet',
    '{
        "pre_money_valuation":      {"type": "monetary"},
        "investment_amount":        {"type": "monetary"},
        "equity_stake":             {"type": "percentage"},
        "liquidation_preference":   {"type": "text"},
        "anti_dilution":            {"type": "text"},
        "board_seats":              {"type": "text"},
        "vesting_schedule":         {"type": "text"},
        "esop_pool":                {"type": "percentage"},
        "drag_along":               {"type": "text"},
        "tag_along":                {"type": "text"},
        "investor_name":            {"type": "text"},
        "company_name":             {"type": "text"}
    }'::jsonb,
    '{
        "valuation":    ["Valuation", "Pre-Money", "Post-Money", "Price Per Share"],
        "investment":   ["Investment", "Funding", "Subscription", "Consideration"],
        "rights":       ["Rights", "Voting Rights", "Protective Provisions", "Information Rights"],
        "liquidation":  ["Liquidation", "Liquidation Preference", "Waterfall", "Distribution"],
        "anti_dilution":["Anti-Dilution", "Dilution Protection", "Ratchet", "Weighted Average"],
        "governance":   ["Governance", "Board", "Board Composition", "Observer Rights"],
        "exit":         ["Exit", "Drag Along", "Tag Along", "IPO", "Acquisition", "ROFR"],
        "vesting":      ["Vesting", "ESOP", "Stock Options", "Cliff"]
    }'::jsonb,
    '["dilution_check", "exit_check", "liquidation_check", "governance_check", "valuation_check", "vesting_check"]'::jsonb,
    '["full_ratchet_anti_dilution", "excessive_liquidation_pref", "no_exit_clause", "founder_vesting_trap", "excessive_board_control", "no_tag_along", "uncapped_esop_dilution"]'::jsonb,
    '{
        "dilution_check": {
            "fields": ["anti_dilution_type", "esop_pool", "equity_stake", "future_rounds_impact"],
            "verdict_format": "Anti-dilution: {anti_dilution_type}. ESOP pool: {esop_pool}. Your equity: {equity_stake}. Impact of future rounds: {future_rounds_impact}."
        },
        "exit_check": {
            "fields": ["drag_along", "tag_along", "rofr", "lock_in"],
            "verdict_format": "Drag-along: {drag_along}. Tag-along: {tag_along}. ROFR: {rofr}. Lock-in: {lock_in}."
        },
        "liquidation_check": {
            "fields": ["liquidation_preference", "participation", "cap"],
            "verdict_format": "Liquidation preference: {liquidation_preference}. Participation: {participation}. Cap: {cap}."
        }
    }'::jsonb,
    'SEBI AIF Regulations, Companies Act 2013, FEMA regulations for foreign investment, DPIIT startup guidelines',
    'term sheet pre-money valuation investment amount equity stake liquidation preference anti-dilution board seats vesting esop drag along tag along investor startup funding round',
    '["term sheet", "pre-money", "valuation", "equity", "liquidation preference", "anti-dilution", "drag along", "tag along", "vesting", "esop", "board seat"]'::jsonb
);
