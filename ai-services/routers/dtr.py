"""DTR router — Document Type Registry API endpoints.

Exposes DTR configs and doc-type-specific features to the frontend
and other consumers.
"""

from __future__ import annotations

from fastapi import APIRouter

from dtr.registry import get_registry
from utils.logging import get_logger

router = APIRouter(prefix="/dtr", tags=["dtr"])
log = get_logger("routers.dtr")


@router.get("/types")
async def list_doc_types():
    """List all enabled document types with their display names and intents."""
    registry = get_registry()
    configs = registry.get_all()
    return [
        {
            "docType": c.doc_type,
            "displayName": c.display_name,
            "queryIntents": c.query_intents,
            "riskPatterns": c.risk_patterns,
            "entityCount": len(c.entity_schema),
            "sectionCount": len(c.section_taxonomy),
        }
        for c in configs
    ]


@router.get("/types/{doc_type}")
async def get_doc_type(doc_type: str):
    """Get full DTR config for a specific document type."""
    registry = get_registry()
    config = registry.get(doc_type)
    return {
        "docType": config.doc_type,
        "displayName": config.display_name,
        "entitySchema": {
            name: {"type": field.type, "pattern": field.pattern}
            for name, field in config.entity_schema.items()
        },
        "sectionTaxonomy": config.section_taxonomy,
        "queryIntents": config.query_intents,
        "riskPatterns": config.risk_patterns,
        "answerTemplates": {
            intent: {"fields": tmpl.fields, "verdictFormat": tmpl.verdict_format}
            for intent, tmpl in config.answer_templates.items()
        },
        "regulatoryContext": config.regulatory_context,
    }


@router.get("/types/{doc_type}/suggested-queries")
async def suggested_queries(doc_type: str):
    """Generate suggested queries for a document type based on its intents."""
    registry = get_registry()
    config = registry.get(doc_type)

    suggestions = []
    # Generate human-readable questions from intents
    _INTENT_QUESTION_MAP = {
        # Insurance
        "coverage_check": "What is my coverage amount and room rent limit?",
        "exclusion_check": "What are the key exclusions in this policy?",
        "claim_process_check": "How do I file a claim and what documents do I need?",
        "waiting_period_check": "What is the waiting period for pre-existing diseases?",
        "premium_check": "What is the premium structure and payment schedule?",
        "network_hospital_check": "Which hospitals are in the network?",
        # Loan
        "repayment_check": "What is my EMI and total repayment amount?",
        "prepayment_penalty_check": "What are the prepayment or foreclosure charges?",
        "default_consequence_check": "What happens if I default on payments?",
        "collateral_check": "What collateral or security is required?",
        "interest_rate_check": "What is the interest rate and is it fixed or floating?",
        "fee_check": "What are the processing fees and other charges?",
        # KYC
        "validity_check": "Is this document currently valid?",
        "expiry_check": "When does this document expire?",
        "address_match_check": "Does the address match across documents?",
        "identity_verify_check": "Can this document verify identity?",
        # Legal
        "obligation_check": "What are the key obligations of each party?",
        "liability_check": "What is the liability cap and indemnification scope?",
        "termination_check": "Under what conditions can this contract be terminated?",
        "jurisdiction_check": "What is the governing law and dispute resolution mechanism?",
        "confidentiality_check": "What are the confidentiality obligations?",
        "indemnification_check": "What does the indemnification clause cover?",
        # Bond
        "covenant_check": "What are the financial covenants?",
        "redemption_check": "What are the redemption terms and call/put options?",
        "rating_change_check": "What happens if the credit rating changes?",
        "yield_check": "What is the coupon rate and yield to maturity?",
        "default_risk_check": "What are the events of default?",
        "security_check": "Is this bond secured or unsecured?",
        # Term Sheet
        "dilution_check": "What anti-dilution protection is included?",
        "exit_check": "What are the drag-along and tag-along provisions?",
        "liquidation_check": "What is the liquidation preference structure?",
        "governance_check": "What is the board composition and voting rights?",
        "valuation_check": "What is the pre-money and post-money valuation?",
        "vesting_check": "What is the vesting schedule for founders?",
    }

    for intent in config.query_intents:
        question = _INTENT_QUESTION_MAP.get(intent)
        if question:
            suggestions.append({
                "intent": intent,
                "question": question,
            })
        else:
            # Generate a readable question from the intent name
            readable = intent.replace("_", " ").replace("check", "").strip()
            suggestions.append({
                "intent": intent,
                "question": f"Tell me about the {readable} in this document.",
            })

    return {"docType": config.doc_type, "suggestions": suggestions}


@router.post("/reload")
async def reload_dtr():
    """Force reload all DTR configs from the backend API."""
    registry = get_registry()
    registry.invalidate_all()
    await registry.load_all()
    configs = registry.get_all()
    return {
        "status": "reloaded",
        "count": len(configs),
        "types": [c.doc_type for c in configs],
    }
