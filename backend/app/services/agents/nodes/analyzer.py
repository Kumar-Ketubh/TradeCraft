import json
import logging
import re
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.finding import FindingCategory
from app.services.agents.state import AgentState
from app.services.agents.llm_factory import LLMProviderFactory

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM_PROMPT = """You are the Impact Analyzer Node in the TradeCraft Competitive Intelligence engine.
Your task is to evaluate the strategic, commercial, and technical impact of a verified competitor move against our product context.

Analyze:
1. Threat Level & Commercial Urgency: Does this threaten our pricing tiers, customer churn, or feature parity?
2. Target Initiative: What concrete countermeasure should our product/engineering team take?
3. Categorization: Choose strictly from: [PRICING_CHANGE, FEATURE_RELEASE, POSITIONING, DEPRECATION, OTHER].

Return strictly valid JSON:
{
  "title": "Clear action-oriented title describing the competitor change",
  "category": "PRICING_CHANGE",
  "impact_analysis": "Detailed assessment of implications for our product and target audience",
  "recommended_action": "Actionable engineering/commercial countermeasure"
}
"""


def impact_analyzer_node(state: AgentState) -> Dict[str, Any]:
    """
    Impact Analyzer Node:
    Evaluates strategic implications by cross-referencing factual observations
    with our workspace's positioning and strategic focus.
    """
    competitor = state.get("competitor_name", "Competitor")
    factual_summary = state.get("factual_summary", "")
    extracted_quotes = state.get("extracted_quotes", [])

    # Workspace Context
    product_name = state.get("product_name", "Our Product")
    value_proposition = state.get("value_proposition", "")
    target_audience = state.get("target_audience", "")
    pricing_summary = state.get("pricing_summary", "")
    strategic_focus = state.get("strategic_focus", "")

    # Critic Feedback (if in a feedback loop)
    critic_notes = state.get("critic_notes", "")
    feedback_section = ""
    if critic_notes:
        feedback_section = f"\nPREVIOUS CRITIC FEEDBACK (Please refine accordingly):\n{critic_notes}\n"

    human_prompt = f"""
OUR PRODUCT CONTEXT:
- Product Name: {product_name}
- Value Proposition: {value_proposition}
- Target Audience: {target_audience}
- Pricing Summary: {pricing_summary}
- Strategic Focus / OKRs: {strategic_focus}

COMPETITOR MOVE:
- Competitor: {competitor}
- Factual Observation: {factual_summary}
- Verified Source Quotes: {extracted_quotes}
{feedback_section}
Produce the JSON object containing "title", "category", "impact_analysis", and "recommended_action".
"""

    llm = LLMProviderFactory.get_chat_model()

    title = f"{competitor} Strategy Adjustment"
    category = FindingCategory.OTHER.value
    impact_analysis = "Competitor updated their web surface, requiring monitoring."
    recommended_action = "Review competitor developments and track user feedback."

    try:
        response = llm.invoke([
            SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
            HumanMessage(content=human_prompt)
        ])

        content = response.content.strip()
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            title = data.get("title", title)
            raw_category = data.get("category", "OTHER").upper()
            if raw_category in FindingCategory.__members__:
                category = raw_category
            else:
                category = FindingCategory.FEATURE_RELEASE.value
            impact_analysis = data.get("impact_analysis", impact_analysis)
            recommended_action = data.get("recommended_action", recommended_action)

    except Exception as exc:
        logger.warning("Impact analyzer LLM exception: %s. Using default analysis.", exc)
        if any("$" in q or "€" in q or "price" in q.lower() for q in extracted_quotes):
            category = FindingCategory.PRICING_CHANGE.value
            title = f"{competitor} Pricing & Subscription Shift"
            impact_analysis = (
                f"Direct threat to {product_name}'s conversion rates and entry-tier value perception."
            )
            recommended_action = (
                f"Assess customer acquisition costs and update sales battlecard against {competitor}."
            )

    return {
        "title": title,
        "category": category,
        "impact_analysis": impact_analysis,
        "recommended_action": recommended_action
    }
