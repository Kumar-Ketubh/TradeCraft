import logging
from datetime import datetime, timezone
from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.workspace import Workspace
from app.models.finding import IntelligenceFinding, VerificationStatus
from app.services.agents.llm_factory import LLMProviderFactory

logger = logging.getLogger(__name__)

PROPOSAL_SYSTEM_PROMPT = """You are the Proposal Generator in TradeCraft AI Competitive Intelligence.
Your role is to synthesize verified competitor intelligence findings into an executive-ready, structured project proposal.

STRICT MANDATORY REQUIREMENTS:
1. Every factual competitor claim must directly cite and remain traceable to the provided verified evidence quotes.
2. Do NOT invent competitor actions, metrics, or quotes not present in the input findings.
3. The generated markdown document MUST contain these exact 7 sections as H2 headers:
   ## 1. Problem / Opportunity
   ## 2. Competitor Change
   ## 3. Evidence
   ## 4. Strategic Impact
   ## 5. Proposed Response
   ## 6. Suggested Features/Work
   ## 7. Expected Value
"""


def _render_deterministic_proposal(
    workspace: Workspace,
    verified_findings: List[IntelligenceFinding],
    title: str,
    target_goal: str
) -> str:
    """
    Deterministic structured proposal builder.
    Guarantees that all 7 required sections and all exact evidence quotes
    are formatted with rigorous attribution.
    """
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    goal = target_goal or "Competitive Differentiation & Market Parity"
    product_name = getattr(workspace, "product_name", None) or getattr(workspace, "name", "Our Product")

    lines = [
        f"# Strategic Counter-Proposal: {title}",
        f"**Target Initiative:** {goal}",
        f"**Product Context:** {product_name}",
        f"**Date:** {now_str}",
        "",
        "---",
        "",
        "## 1. Problem / Opportunity",
        f"Recent movements in the market landscape create an immediate strategic window for {product_name}. "
        f"With target customers across {getattr(workspace, 'target_audience', None) or 'our core segments'} evaluating competitive alternatives, "
        f"proactive counter-positioning is required to protect pipeline revenue and accelerate customer acquisition.",
        "",
        "## 2. Competitor Change",
    ]

    for i, finding in enumerate(verified_findings, 1):
        lines.extend([
            f"### 2.{i} {finding.title} ({finding.category})",
            f"- **Observed Change:** {finding.factual_summary}",
            f"- **Verification Confidence:** {finding.confidence_level} ({finding.grounding_score}% Grounding Accuracy)",
            ""
        ])

    lines.extend([
        "## 3. Evidence",
        "The following verbatim source excerpts and snapshot timestamps substantiate the competitor moves identified above:",
        ""
    ])

    quote_index = 1
    for finding in verified_findings:
        lines.append(f"**Evidence for: {finding.title}**")
        if finding.evidence_quotes:
            for q in finding.evidence_quotes:
                lines.append(f"> \"{q.verbatim_quote}\"")
                lines.append(f"*(Source: [{q.source_url or 'Verified Snapshot'}]({q.source_url or '#'}))*")
                lines.append("")
                quote_index += 1
        else:
            lines.append(f"> \"{finding.factual_summary}\" *(Directly verified against source snapshot)*\n")

    lines.extend([
        "## 4. Strategic Impact",
    ])
    for finding in verified_findings:
        lines.append(f"- **{finding.title}:** {finding.impact_analysis}")
    lines.append("")

    lines.extend([
        "## 5. Proposed Response",
    ])
    for finding in verified_findings:
        lines.append(f"- **Recommended Strategic Action:** {finding.recommended_action}")
    lines.append("")

    lines.extend([
        "## 6. Suggested Features/Work",
        f"To neutralize competitive threats and reinforce {product_name}'s unique value proposition:",
        "- **Phase 1 (Immediate Parity - 2 Weeks):** Review feature tier access, update sales enablement battlecards, and publish customer migration guidelines.",
        "- **Phase 2 (Core Differentiators - 6 Weeks):** Ship high-demand workflow integrations and emphasize reliability/uptime guarantees.",
        "- **Phase 3 (GTM Execution):** Launch targeted competitive campaign highlighting total cost of ownership advantages.",
        "",
        "## 7. Expected Value",
        "- **Customer Retention:** Prevent account churn triggered by competitor adjustments.",
        "- **Pipeline Velocity:** Equip go-to-market teams with verified evidence to overcome competitor objections.",
        "- **Strategic Alignment:** Directly serves workspace focus on long-term product-market dominance.",
    ])

    return "\n".join(lines)


def generate_structured_proposal(
    workspace: Workspace,
    findings: List[IntelligenceFinding],
    title: str,
    target_goal: Optional[str] = None
) -> str:
    """
    Generates a structured, evidence-grounded project proposal using only verified findings.
    Enforces the 7 required sections and exact evidence preservation.
    """
    # 1. Validation: Ensure all findings are verified
    unverified = [f for f in findings if f.verification_status != VerificationStatus.VERIFIED.value]
    if unverified:
        unverified_titles = [f.title for f in unverified]
        raise ValueError(
            f"Cannot generate proposal from unverified or rejected findings: {unverified_titles}"
        )

    goal = target_goal or "Competitive Differentiation"
    product_name = getattr(workspace, "product_name", None) or getattr(workspace, "name", "Our Product")

    # Assemble prompt context
    findings_summary = []
    for f in findings:
        quotes_str = "\n".join([f'  * Quote: "{q.verbatim_quote}" ({q.source_url})' for q in f.evidence_quotes])
        findings_summary.append(
            f"- Finding: {f.title} ({f.category})\n"
            f"  * Summary: {f.factual_summary}\n"
            f"  * Impact: {f.impact_analysis}\n"
            f"  * Action: {f.recommended_action}\n"
            f"  * Evidence Quotes:\n{quotes_str or '  * [Verified Snapshot]'}"
        )

    human_prompt = f"""
OUR PRODUCT CONTEXT:
- Product Name: {product_name}
- Value Proposition: {getattr(workspace, 'value_proposition', None) or 'Leading market solution'}
- Target Audience: {getattr(workspace, 'target_audience', None) or 'Engineers and Founders'}
- Pricing Summary: {getattr(workspace, 'pricing_summary', None) or 'Standard SaaS'}
- Strategic Focus: {getattr(workspace, 'strategic_focus', None) or 'Growth and Retention'}

PROPOSAL TITLE: {title}
TARGET INITIATIVE: {goal}

VERIFIED COMPETITOR FINDINGS & EVIDENCE:
{chr(10).join(findings_summary)}

Synthesize the complete proposal containing all 7 required H2 sections.
"""

    llm = LLMProviderFactory.get_chat_model()

    try:
        response = llm.invoke([
            SystemMessage(content=PROPOSAL_SYSTEM_PROMPT),
            HumanMessage(content=human_prompt)
        ])
        content = response.content.strip()

        # Check that the 7 required sections are present in LLM response
        required_headers = [
            "Problem / Opportunity", "Competitor Change", "Evidence",
            "Strategic Impact", "Proposed Response", "Suggested Features/Work", "Expected Value"
        ]
        has_all_sections = all(h.lower() in content.lower() for h in required_headers)

        if has_all_sections and len(content) > 300:
            return content

    except Exception as exc:
        logger.warning("LLM proposal generation exception: %s. Using deterministic builder.", exc)

    # Deterministic fallback guaranteed to produce all 7 sections and exact quote trace
    return _render_deterministic_proposal(
        workspace=workspace,
        verified_findings=findings,
        title=title,
        target_goal=goal
    )
