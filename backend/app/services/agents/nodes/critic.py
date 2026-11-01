import re
import logging
from typing import Dict, Any, List
from app.models.finding import ConfidenceLevel, VerificationStatus
from app.services.agents.state import AgentState, GroundedQuote

logger = logging.getLogger(__name__)


def _normalize_search_string(text: str) -> str:
    """Normalize whitespace for resilient substring search."""
    return re.sub(r"\s+", " ", text).strip().lower()


def critic_verifier_node(state: AgentState) -> Dict[str, Any]:
    """
    Critic / Verifier Node (Hallucination & Grounding Guard):
    1. Validates candidate quotes against the raw snapshot text.
    2. Maps character offsets for frontend evidence highlighting.
    3. Calculates Evidence Grounding Accuracy (EGA).
    4. Enforces the project rule: claims without retained snapshot evidence are rejected or downgraded.
    """
    snapshot_text = state.get("snapshot_text", "")
    source_url = state.get("source_url", "")
    extracted_quotes = state.get("extracted_quotes", [])
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 2)

    normalized_snapshot = _normalize_search_string(snapshot_text)

    verified_quotes: List[GroundedQuote] = []
    unsupported_claims: List[str] = []

    # Verify each extracted quote against snapshot text
    for raw_quote in extracted_quotes:
        cleaned_quote = raw_quote.strip()
        if not cleaned_quote:
            continue

        normalized_quote = _normalize_search_string(cleaned_quote)

        # Look for match in normalized text
        idx = normalized_snapshot.find(normalized_quote)
        if idx != -1:
            orig_match = re.search(re.escape(cleaned_quote), snapshot_text, re.IGNORECASE)
            if orig_match:
                start_offset = orig_match.start()
                end_offset = orig_match.end()
            else:
                start_offset = idx
                end_offset = idx + len(cleaned_quote)

            verified_quotes.append({
                "verbatim_quote": cleaned_quote,
                "char_offset_start": start_offset,
                "char_offset_end": end_offset,
                "source_url": source_url
            })
        else:
            unsupported_claims.append(cleaned_quote)

    total_claims = max(1, len(extracted_quotes))
    substantiated_count = len(verified_quotes)
    ega_score = (substantiated_count / total_claims) * 100.0

    if ega_score >= 85.0:
        verification_status = VerificationStatus.VERIFIED.value
        confidence_level = (
            ConfidenceLevel.HIGH.value if ega_score == 100.0 else ConfidenceLevel.MEDIUM.value
        )
        critic_notes = (
            f"Critic verified: {substantiated_count}/{total_claims} claims substantiated "
            f"with exact snapshot evidence (EGA: {ega_score:.1f}%)."
        )
        next_step = "save"

    else:
        if iteration < max_iterations:
            verification_status = VerificationStatus.DOWNGRADED.value
            confidence_level = ConfidenceLevel.LOW.value
            critic_notes = (
                f"Critic rejection: {len(unsupported_claims)} claims could not be verified "
                f"against source snapshot: {unsupported_claims}. Please revise or remove."
            )
            next_step = "retry_analyzer"
            iteration += 1

        else:
            if ega_score >= 40.0:
                verification_status = VerificationStatus.DOWNGRADED.value
                confidence_level = ConfidenceLevel.LOW.value
                critic_notes = (
                    f"Critic downgraded finding to LOW confidence due to partial grounding "
                    f"({substantiated_count}/{total_claims} verified, EGA: {ega_score:.1f}%)."
                )
            else:
                verification_status = VerificationStatus.REJECTED.value
                confidence_level = ConfidenceLevel.LOW.value
                critic_notes = (
                    f"Critic rejected finding: insufficient factual grounding in source snapshot "
                    f"(EGA: {ega_score:.1f}% < 40%). Claims discarded."
                )
            next_step = "save"

    return {
        "verified_quotes": verified_quotes,
        "unsupported_claims": unsupported_claims,
        "grounding_score": round(ega_score, 1),
        "confidence_level": confidence_level,
        "verification_status": verification_status,
        "critic_notes": critic_notes,
        "iteration": iteration,
        "next_step": next_step
    }
