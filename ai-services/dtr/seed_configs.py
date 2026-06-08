"""Hardcoded fallback DTR configs — used when the database is unreachable.

These mirror the V5 migration seed data so the AI service can start even
without PostgreSQL connectivity.  Keep in sync with the migration.
"""

from __future__ import annotations

from dtr.models import AnswerTemplate, DTRConfig, EntityField

# ─── Insurance Policy ────────────────────────────────────────────────────────

INSURANCE_POLICY = DTRConfig(
    doc_type="insurance_policy",
    display_name="Insurance Policy",
    entity_schema={
        "policy_number":   EntityField(type="text"),
        "sum_insured":     EntityField(type="monetary"),
        "premium":         EntityField(type="monetary"),
        "copay":           EntityField(type="percentage"),
        "deductible":      EntityField(type="monetary"),
        "waiting_period":  EntityField(type="duration"),
        "room_rent_limit": EntityField(type="monetary"),
        "insurer_name":    EntityField(type="text"),
        "hospital":        EntityField(type="text"),
    },
    section_taxonomy={
        "coverage":       ["Coverage", "Benefit", "Sum Insured", "Room Rent", "Cashless"],
        "exclusion":      ["Exclusion", "Not Covered", "Excluded", "Limitations", "Permanent Exclusion"],
        "waiting_period": ["Waiting Period", "Pre-existing", "PED", "Survival Period"],
        "claim_rule":     ["Claim", "Documents Required", "Intimation", "Settlement", "Deductible", "Co-pay"],
        "definition":     ["Definition", "Means", "Interpretation"],
        "renewal":        ["Renewal", "Cancellation", "Termination", "Grace Period"],
    },
    query_intents=[
        "coverage_check", "exclusion_check", "claim_process_check",
        "waiting_period_check", "premium_check", "network_hospital_check",
    ],
    risk_patterns=[
        "hidden_exclusion", "low_sum_insured", "high_copay",
        "short_free_look", "sub_limit_trap", "no_restoration_benefit",
    ],
    answer_templates={
        "coverage_check": AnswerTemplate(
            fields=["sum_insured", "room_rent_limit", "copay", "deductible"],
            verdict_format="Your sum insured is ₹{sum_insured}. Room rent limit: {room_rent_limit}. Co-pay: {copay}. Deductible: ₹{deductible}.",
        ),
        "exclusion_check": AnswerTemplate(
            fields=["exclusion_list", "waiting_period"],
            verdict_format="Key exclusions found: {exclusion_list}. Waiting period for pre-existing diseases: {waiting_period}.",
        ),
        "claim_process_check": AnswerTemplate(
            fields=["claim_intimation_period", "documents_required"],
            verdict_format="Claim must be intimated within {claim_intimation_period}. Required documents: {documents_required}.",
        ),
    },
    regulatory_context="IRDAI regulations, Insurance Act 1938, IRDAI (Health Insurance) Regulations",
    classifier_exemplar=(
        "insurance policy schedule sum insured premium exclusions waiting period "
        "coverage benefits room rent deductible co-pay renewal terms policy number"
    ),
    classifier_terms=[
        "policy number", "sum insured", "premium", "exclusions",
        "waiting period", "co-pay", "copay", "deductible", "room rent",
    ],
)


# ─── Loan Agreement ──────────────────────────────────────────────────────────

LOAN_AGREEMENT = DTRConfig(
    doc_type="loan_agreement",
    display_name="Loan Agreement",
    entity_schema={
        "principal":           EntityField(type="monetary"),
        "interest_rate":       EntityField(type="percentage"),
        "emi":                 EntityField(type="monetary"),
        "tenure":              EntityField(type="duration"),
        "prepayment_penalty":  EntityField(type="percentage"),
        "collateral":          EntityField(type="asset"),
        "processing_fee":      EntityField(type="monetary"),
        "late_payment_charge": EntityField(type="percentage"),
        "loan_account_number": EntityField(type="text"),
        "borrower_name":       EntityField(type="text"),
        "lender_name":         EntityField(type="text"),
    },
    section_taxonomy={
        "terms":      ["Loan Terms", "Principal Amount", "Interest Rate", "Rate of Interest"],
        "repayment":  ["EMI Schedule", "Repayment", "Instalment", "Payment Schedule"],
        "default":    ["Events of Default", "Default", "Non-Payment", "Acceleration"],
        "security":   ["Collateral", "Mortgage", "Security Interest", "Hypothecation", "Pledge"],
        "fees":       ["Processing Fee", "Charges", "Fees", "Stamp Duty"],
        "prepayment": ["Prepayment", "Foreclosure", "Part Payment", "Early Repayment"],
    },
    query_intents=[
        "repayment_check", "prepayment_penalty_check",
        "default_consequence_check", "collateral_check",
        "interest_rate_check", "fee_check",
    ],
    risk_patterns=[
        "floating_rate_unilateral_change", "cross_default_clause",
        "hidden_processing_fee", "excessive_late_fee",
        "no_prepayment_option", "blanket_lien",
    ],
    answer_templates={
        "repayment_check": AnswerTemplate(
            fields=["emi", "tenure", "total_interest", "rate_type"],
            verdict_format="Your EMI is ₹{emi} for {tenure} months. Total interest = ₹{total_interest}. Rate type: {rate_type}.",
        ),
        "prepayment_penalty_check": AnswerTemplate(
            fields=["prepayment_penalty", "lock_in_period", "conditions"],
            verdict_format="Prepayment penalty: {prepayment_penalty}. Lock-in period: {lock_in_period}. {conditions}",
        ),
        "default_consequence_check": AnswerTemplate(
            fields=["default_triggers", "consequences", "cure_period"],
            verdict_format="Default triggers: {default_triggers}. Consequences: {consequences}. Cure period: {cure_period}.",
        ),
    },
    regulatory_context="RBI lending norms, FEMA guidelines, NHB regulations for home loans, RBI Fair Practices Code",
    classifier_exemplar=(
        "loan agreement principal amount interest rate emi equated monthly instalment "
        "tenure repayment prepayment penalty collateral mortgage security borrower lender"
    ),
    classifier_terms=[
        "loan", "principal", "interest rate", "emi", "equated monthly",
        "mortgage", "collateral", "borrower", "lender", "repayment",
    ],
)


# ─── KYC Document ─────────────────────────────────────────────────────────────

KYC_DOCUMENT = DTRConfig(
    doc_type="kyc_document",
    display_name="KYC Document",
    entity_schema={
        "document_number":   EntityField(type="text"),
        "full_name":         EntityField(type="text"),
        "date_of_birth":     EntityField(type="date"),
        "address":           EntityField(type="text"),
        "expiry_date":       EntityField(type="date"),
        "issue_date":        EntityField(type="date"),
        "issuing_authority": EntityField(type="text"),
        "document_class":    EntityField(type="text"),
    },
    section_taxonomy={
        "identity":  ["Identity", "Name", "Photo", "Photograph"],
        "address":   ["Address", "Residence", "Permanent Address", "Correspondence"],
        "validity":  ["Valid", "Expiry", "Issue Date", "Validity Period"],
        "authority": ["Issued By", "Government of India", "Authority"],
    },
    query_intents=["validity_check", "expiry_check", "address_match_check", "identity_verify_check"],
    risk_patterns=["expired_document", "mismatched_name", "address_discrepancy", "tampered_document", "missing_photo"],
    answer_templates={
        "validity_check": AnswerTemplate(
            fields=["document_number", "issue_date", "expiry_date", "status"],
            verdict_format="Document {document_number} issued on {issue_date}. Expiry: {expiry_date}. Status: {status}.",
        ),
        "expiry_check": AnswerTemplate(
            fields=["expiry_date", "days_remaining"],
            verdict_format="Document expires on {expiry_date}. {days_remaining} days remaining.",
        ),
    },
    regulatory_context="RBI KYC Master Direction, PMLA 2002, SEBI KYC norms, UIDAI Aadhaar guidelines",
    classifier_exemplar=(
        "aadhaar pan card identity proof address proof kyc date of birth "
        "government identification number passport voter id driving licence"
    ),
    classifier_terms=[
        "aadhaar", "pan card", "kyc", "identity proof", "address proof",
        "passport", "voter id", "driving licence",
    ],
)


# ─── Legal Contract ───────────────────────────────────────────────────────────

LEGAL_CONTRACT = DTRConfig(
    doc_type="legal_contract",
    display_name="Legal Contract",
    entity_schema={
        "parties":              EntityField(type="text"),
        "effective_date":       EntityField(type="date"),
        "termination_clause":   EntityField(type="text"),
        "liability_cap":        EntityField(type="monetary"),
        "jurisdiction":         EntityField(type="text"),
        "governing_law":        EntityField(type="text"),
        "indemnification":      EntityField(type="text"),
        "confidentiality_term": EntityField(type="duration"),
        "notice_period":        EntityField(type="duration"),
    },
    section_taxonomy={
        "parties":       ["Parties", "Between", "Party A", "Party B", "First Party", "Second Party"],
        "obligations":   ["Obligations", "Duties", "Responsibilities", "Covenants", "Undertakings"],
        "liability":     ["Liability", "Indemnification", "Indemnity", "Damages", "Limitation of Liability"],
        "termination":   ["Termination", "Expiry", "Cancellation", "Exit", "Break Clause"],
        "confidential":  ["Confidentiality", "Non-Disclosure", "NDA", "Trade Secret"],
        "dispute":       ["Dispute Resolution", "Arbitration", "Jurisdiction", "Governing Law"],
        "general":       ["Miscellaneous", "General Provisions", "Force Majeure", "Severability"],
    },
    query_intents=[
        "obligation_check", "liability_check", "termination_check",
        "jurisdiction_check", "confidentiality_check", "indemnification_check",
    ],
    risk_patterns=[
        "unlimited_liability", "unilateral_termination", "unfavorable_jurisdiction",
        "one_sided_indemnity", "no_force_majeure", "auto_renewal_trap", "non_compete_overreach",
    ],
    answer_templates={
        "obligation_check": AnswerTemplate(
            fields=["party_obligations", "deadlines", "penalties"],
            verdict_format="Key obligations: {party_obligations}. Deadlines: {deadlines}. Non-compliance penalties: {penalties}.",
        ),
        "liability_check": AnswerTemplate(
            fields=["liability_cap", "indemnification_scope", "exclusions"],
            verdict_format="Liability cap: {liability_cap}. Indemnification covers: {indemnification_scope}. Excluded: {exclusions}.",
        ),
        "termination_check": AnswerTemplate(
            fields=["termination_triggers", "notice_period", "consequences"],
            verdict_format="Termination triggers: {termination_triggers}. Notice period: {notice_period}. Post-termination: {consequences}.",
        ),
    },
    regulatory_context="Indian Contract Act 1872, Specific Relief Act, Arbitration and Conciliation Act 1996",
    classifier_exemplar=(
        "agreement contract between parties hereby agrees obligations liability "
        "indemnification termination governing law jurisdiction arbitration confidentiality"
    ),
    classifier_terms=[
        "agreement", "contract", "hereby", "parties", "obligations",
        "indemnification", "termination", "jurisdiction", "arbitration", "governing law",
    ],
)


# ─── Bond / Debenture ────────────────────────────────────────────────────────

BOND_INSTRUMENT = DTRConfig(
    doc_type="bond_instrument",
    display_name="Bond / Debenture",
    entity_schema={
        "face_value":        EntityField(type="monetary"),
        "coupon_rate":       EntityField(type="percentage"),
        "maturity_date":     EntityField(type="date"),
        "yield_to_maturity": EntityField(type="percentage"),
        "credit_rating":     EntityField(type="text"),
        "issuer":            EntityField(type="text"),
        "trustee":           EntityField(type="text"),
        "isin":              EntityField(type="text"),
        "call_date":         EntityField(type="date"),
        "put_date":          EntityField(type="date"),
    },
    section_taxonomy={
        "terms":      ["Terms of Issue", "Face Value", "Coupon", "Interest Payment"],
        "covenants":  ["Covenants", "Restrictive Covenants", "Affirmative Covenants", "Financial Covenants"],
        "redemption": ["Redemption", "Maturity", "Call Option", "Put Option", "Buyback"],
        "security":   ["Security", "Secured", "Unsecured", "Charge", "Debenture Trust Deed"],
        "default":    ["Events of Default", "Cross Default", "Acceleration"],
        "rating":     ["Credit Rating", "Rating", "CRISIL", "ICRA", "CARE"],
    },
    query_intents=[
        "covenant_check", "redemption_check", "rating_change_check",
        "yield_check", "default_risk_check", "security_check",
    ],
    risk_patterns=[
        "covenant_breach_risk", "call_risk", "credit_downgrade",
        "subordination_risk", "no_put_option", "cross_default_trigger",
    ],
    answer_templates={
        "covenant_check": AnswerTemplate(
            fields=["covenants_list", "financial_ratios", "compliance_status"],
            verdict_format="Key covenants: {covenants_list}. Financial ratio requirements: {financial_ratios}. Compliance: {compliance_status}.",
        ),
        "redemption_check": AnswerTemplate(
            fields=["maturity_date", "call_date", "put_date", "redemption_premium"],
            verdict_format="Maturity: {maturity_date}. Call option: {call_date}. Put option: {put_date}. Redemption premium: {redemption_premium}.",
        ),
        "yield_check": AnswerTemplate(
            fields=["coupon_rate", "yield_to_maturity", "credit_rating"],
            verdict_format="Coupon: {coupon_rate}. YTM: {yield_to_maturity}. Credit rating: {credit_rating}.",
        ),
    },
    regulatory_context="SEBI (Issue and Listing of Non-Convertible Securities) Regulations 2021, RBI guidelines on corporate bonds, SEBI LODR",
    classifier_exemplar=(
        "bond debenture face value coupon rate maturity yield credit rating "
        "issuer trustee isin call put redemption covenant"
    ),
    classifier_terms=[
        "bond", "debenture", "coupon", "maturity", "yield",
        "credit rating", "isin", "trustee", "face value", "redemption",
    ],
)


# ─── Term Sheet ───────────────────────────────────────────────────────────────

TERM_SHEET = DTRConfig(
    doc_type="term_sheet",
    display_name="Term Sheet",
    entity_schema={
        "pre_money_valuation":    EntityField(type="monetary"),
        "investment_amount":      EntityField(type="monetary"),
        "equity_stake":           EntityField(type="percentage"),
        "liquidation_preference": EntityField(type="text"),
        "anti_dilution":          EntityField(type="text"),
        "board_seats":            EntityField(type="text"),
        "vesting_schedule":       EntityField(type="text"),
        "esop_pool":              EntityField(type="percentage"),
        "drag_along":             EntityField(type="text"),
        "tag_along":              EntityField(type="text"),
        "investor_name":          EntityField(type="text"),
        "company_name":           EntityField(type="text"),
    },
    section_taxonomy={
        "valuation":     ["Valuation", "Pre-Money", "Post-Money", "Price Per Share"],
        "investment":    ["Investment", "Funding", "Subscription", "Consideration"],
        "rights":        ["Rights", "Voting Rights", "Protective Provisions", "Information Rights"],
        "liquidation":   ["Liquidation", "Liquidation Preference", "Waterfall", "Distribution"],
        "anti_dilution": ["Anti-Dilution", "Dilution Protection", "Ratchet", "Weighted Average"],
        "governance":    ["Governance", "Board", "Board Composition", "Observer Rights"],
        "exit":          ["Exit", "Drag Along", "Tag Along", "IPO", "Acquisition", "ROFR"],
        "vesting":       ["Vesting", "ESOP", "Stock Options", "Cliff"],
    },
    query_intents=[
        "dilution_check", "exit_check", "liquidation_check",
        "governance_check", "valuation_check", "vesting_check",
    ],
    risk_patterns=[
        "full_ratchet_anti_dilution", "excessive_liquidation_pref",
        "no_exit_clause", "founder_vesting_trap", "excessive_board_control",
        "no_tag_along", "uncapped_esop_dilution",
    ],
    answer_templates={
        "dilution_check": AnswerTemplate(
            fields=["anti_dilution_type", "esop_pool", "equity_stake", "future_rounds_impact"],
            verdict_format="Anti-dilution: {anti_dilution_type}. ESOP pool: {esop_pool}. Your equity: {equity_stake}. Impact of future rounds: {future_rounds_impact}.",
        ),
        "exit_check": AnswerTemplate(
            fields=["drag_along", "tag_along", "rofr", "lock_in"],
            verdict_format="Drag-along: {drag_along}. Tag-along: {tag_along}. ROFR: {rofr}. Lock-in: {lock_in}.",
        ),
        "liquidation_check": AnswerTemplate(
            fields=["liquidation_preference", "participation", "cap"],
            verdict_format="Liquidation preference: {liquidation_preference}. Participation: {participation}. Cap: {cap}.",
        ),
    },
    regulatory_context="SEBI AIF Regulations, Companies Act 2013, FEMA regulations for foreign investment, DPIIT startup guidelines",
    classifier_exemplar=(
        "term sheet pre-money valuation investment amount equity stake liquidation preference "
        "anti-dilution board seats vesting esop drag along tag along investor startup funding round"
    ),
    classifier_terms=[
        "term sheet", "pre-money", "valuation", "equity", "liquidation preference",
        "anti-dilution", "drag along", "tag along", "vesting", "esop", "board seat",
    ],
)


# ─── All seeds as a dict ─────────────────────────────────────────────────────

SEED_CONFIGS: dict[str, DTRConfig] = {
    cfg.doc_type: cfg
    for cfg in [
        INSURANCE_POLICY,
        LOAN_AGREEMENT,
        KYC_DOCUMENT,
        LEGAL_CONTRACT,
        BOND_INSTRUMENT,
        TERM_SHEET,
    ]
}
"""All hardcoded seed configs keyed by doc_type. Used as fallback."""
