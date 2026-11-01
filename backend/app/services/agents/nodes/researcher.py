import json
import logging
import re
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.agents.state import AgentState
from app.services.agents.llm_factory import LLMProviderFactory

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = """You are the Context Researcher Node in the TradeCraft Competitive Intelligence engine.
Your task is to analyze candidate content diffs from a competitor's web channel and produce a concise, factual summary.

STRICT GROUNDING RULES:
1. Extract ONLY factual changes directly demonstrated by the provided diff and snapshot text.
2. For every factual claim you make, identify 1-3 short verbatim quotes (5-15 words each) from the snapshot text that directly substantiate it.
3. NEVER make assumptions, extrapolate rumors, or hallucinate claims not present in the text.
4. Output your response strictly in valid JSON format:
{
  "factual_summary": "Concise factual summary of the change",
  "extracted_quotes": ["exact verbatim quote 1", "exact verbatim quote 2"]
}
"""


def _extract_fallback_quotes(candidate_diff: str, snapshot_text: str) -> List[str]:
    """Fallback: extract added lines from diff that literally appear in the snapshot."""
    quotes = []
    for line in candidate_diff.splitlines():
        line = line.strip()
        if line.startswith("+") and not line.startswith("+++"):
            clean_line = line[1:].strip()
            if len(clean_line) >= 5 and clean_line.lower() in snapshot_text.lower():
                quotes.append(clean_line)
                if len(quotes) >= 3:
                    break
    return quotes or ["Verified competitor text update"]


def context_researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Context Researcher Node:
    Analyzes candidate diffs in the context of the snapshot text to produce
    grounded factual observations and candidate source quotes.
    """
    competitor = state.get("competitor_name", "Competitor")
    source_url = state.get("source_url", "")
    candidate_diff = state.get("candidate_diff", "")
    snapshot_text = state.get("snapshot_text", "")

    # Truncate snapshot context for LLM prompt safety
    truncated_snapshot = snapshot_text[:4000] if snapshot_text else "No snapshot text"

    human_prompt = f"""
Competitor: {competitor}
Source URL: {source_url}

Candidate Diff:
```diff
{candidate_diff}
```

Current Snapshot Text Excerpt:
```text
{truncated_snapshot}
```

Produce the JSON object containing "factual_summary" and "extracted_quotes".
"""

    llm = LLMProviderFactory.get_chat_model()

    try:
        response = llm.invoke([
            SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
            HumanMessage(content=human_prompt)
        ])

        # Parse JSON
        content = response.content.strip()
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            factual_summary = data.get("factual_summary", "")
            extracted_quotes = data.get("extracted_quotes", [])
        else:
            factual_summary = content
            extracted_quotes = _extract_fallback_quotes(candidate_diff, snapshot_text)

    except Exception as exc:
        logger.warning("Context researcher LLM parsing exception: %s. Using heuristic fallback.", exc)
        factual_summary = f"Detected competitor update on {competitor} ({source_url})"
        extracted_quotes = _extract_fallback_quotes(candidate_diff, snapshot_text)

    if not extracted_quotes:
        extracted_quotes = _extract_fallback_quotes(candidate_diff, snapshot_text)

    return {
        "factual_summary": factual_summary,
        "extracted_quotes": extracted_quotes
    }
