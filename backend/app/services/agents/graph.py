import logging
from typing import Optional, Dict, Any, Union
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.models.change import Change
from app.models.snapshot import Snapshot
from app.models.source import Source
from app.models.competitor import Competitor
from app.models.workspace import Workspace
from app.models.finding import IntelligenceFinding, EvidenceQuote, VerificationStatus
from app.services.agents.state import AgentState
from app.services.agents.nodes.researcher import context_researcher_node
from app.services.agents.nodes.analyzer import impact_analyzer_node
from app.services.agents.nodes.critic import critic_verifier_node

logger = logging.getLogger(__name__)


def route_critic(state: AgentState) -> str:
    """Conditional routing based on Critic Verifier's determination."""
    next_step = state.get("next_step", "save")
    if next_step == "retry_analyzer":
        return "retry_analyzer"
    return "save"


def build_intelligence_graph():
    """
    Constructs and compiles the LangGraph StateGraph workflow:
    Change -> Context Researcher -> Impact Analyzer -> Critic/Verifier -> Output / Loop
    """
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("context_researcher", context_researcher_node)
    workflow.add_node("impact_analyzer", impact_analyzer_node)
    workflow.add_node("critic_verifier", critic_verifier_node)

    # Define edges
    workflow.set_entry_point("context_researcher")
    workflow.add_edge("context_researcher", "impact_analyzer")
    workflow.add_edge("impact_analyzer", "critic_verifier")

    # Conditional feedback loop: if critic rejects unsupported claims, retry analyzer
    workflow.add_conditional_edges(
        "critic_verifier",
        route_critic,
        {
            "retry_analyzer": "impact_analyzer",
            "save": END
        }
    )

    return workflow.compile()


# Global compiled graph instance
intelligence_graph = build_intelligence_graph()


def run_agent_pipeline(
    change_id: str,
    db: Session,
    candidate_diff_id: Optional[str] = None
) -> Optional[IntelligenceFinding]:
    """
    Executes the LangGraph agent pipeline for a given change record and persists
    the resulting intelligence finding and grounded evidence quotes.
    """
    target_id = change_id or candidate_diff_id
    if not target_id:
        logger.error("No change_id provided for agent pipeline execution.")
        return None

    # 1. Fetch Change and associated entities
    change = db.query(Change).filter(Change.id == target_id).first()
    if not change:
        logger.error("Change record %s not found for agent execution.", target_id)
        return None

    # Fetch snapshot
    snapshot = db.query(Snapshot).filter(Snapshot.id == change.current_snapshot_id).first()
    if not snapshot:
        logger.error("Current snapshot %s not found for change %s.", change.current_snapshot_id, target_id)
        return None

    # Fetch source, competitor, and workspace
    source = db.query(Source).filter(Source.id == change.source_id).first()
    competitor = db.query(Competitor).filter(Competitor.id == change.competitor_id).first()
    workspace = db.query(Workspace).filter(Workspace.id == change.workspace_id).first()

    if not workspace:
        logger.error("Workspace hierarchy missing for change %s.", target_id)
        return None

    competitor_name = competitor.name if competitor else "Competitor"
    source_url = source.url if source else ""
    product_name = (
        getattr(workspace, "product_name", None)
        or getattr(workspace, "name", "Our Product")
    )

    # 2. Assemble initial AgentState
    initial_state: AgentState = {
        "workspace_id": workspace.id,
        "candidate_diff_id": change.id,
        "change_id": change.id,
        "snapshot_id": snapshot.id,
        "source_url": source_url,
        "source_type": getattr(source, "source_type", "web"),
        "competitor_name": competitor_name,
        "product_name": product_name,
        "value_proposition": getattr(workspace, "value_proposition", "") or "",
        "target_audience": getattr(workspace, "target_audience", "") or "",
        "pricing_summary": getattr(workspace, "pricing_summary", "") or "",
        "strategic_focus": getattr(workspace, "strategic_focus", "") or "",
        "candidate_diff": change.diff_unified or "",
        "snapshot_text": snapshot.normalized_content or snapshot.raw_content or "",
        "iteration": 1,
        "max_iterations": 2,
    }

    # 3. Execute LangGraph workflow synchronously
    logger.info("Executing LangGraph intelligence workflow for change %s...", change.id)
    try:
        final_state: AgentState = intelligence_graph.invoke(initial_state)
    except Exception as exc:
        logger.exception("Agent workflow execution error: %s", exc)
        return None

    # 4. Persist Intelligence Finding
    finding = IntelligenceFinding(
        workspace_id=workspace.id,
        change_id=change.id,
        title=final_state.get("title", f"{competitor_name} Move"),
        category=final_state.get("category", "OTHER"),
        factual_summary=final_state.get("factual_summary", ""),
        impact_analysis=final_state.get("impact_analysis", ""),
        recommended_action=final_state.get("recommended_action", ""),
        confidence_level=final_state.get("confidence_level", "MEDIUM"),
        verification_status=final_state.get("verification_status", VerificationStatus.VERIFIED.value),
        critic_notes=final_state.get("critic_notes", ""),
        grounding_score=final_state.get("grounding_score", 100.0),
    )
    db.add(finding)
    db.flush()

    # 5. Persist Verified Evidence Quotes
    verified_quotes = final_state.get("verified_quotes", [])
    for q in verified_quotes:
        quote_record = EvidenceQuote(
            finding_id=finding.id,
            snapshot_id=snapshot.id,
            verbatim_quote=q["verbatim_quote"],
            char_offset_start=q.get("char_offset_start"),
            char_offset_end=q.get("char_offset_end"),
            source_url=q.get("source_url", source_url)
        )
        db.add(quote_record)

    db.commit()
    db.refresh(finding)

    logger.info(
        "Successfully created IntelligenceFinding %s (%s, EGA: %.1f%%) with %d evidence quotes.",
        finding.id, finding.verification_status, finding.grounding_score, len(verified_quotes)
    )
    return finding
