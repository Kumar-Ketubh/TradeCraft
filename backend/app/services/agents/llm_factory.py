import json
import logging
import re
from typing import Any, List, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration

from app.core.config import settings

logger = logging.getLogger(__name__)


class MockDeterministicChatModel(BaseChatModel):
    """
    Zero-dependency deterministic LLM mock.
    Used for local testing, offline development, or when external API keys are unavailable.
    Inspects user prompt and extracts factual claims and grounded quotes from the provided text.
    """
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_message_content = messages[-1].content if messages else ""

        # Check if this is the Context Researcher prompt
        if "Context Researcher" in last_message_content or "candidate_diff" in last_message_content:
            price_match = re.search(r"(\$|€|£)\s*\d+([^\n]*)", last_message_content)
            quote = price_match.group(0).strip() if price_match else "Substantive change in feature offerings"

            response_json = {
                "factual_summary": f"Detected verified update: {quote}",
                "extracted_quotes": [quote]
            }
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=json.dumps(response_json)))])

        # Check if this is the Impact Analyzer prompt
        elif "Impact Analyzer" in last_message_content or "strategic implications" in last_message_content:
            response_json = {
                "title": "Competitor Commercial Structure Adjustment",
                "category": "PRICING_CHANGE",
                "impact_analysis": (
                    "The competitor has adjusted their tier specifications and pricing points. "
                    "This puts pressure on our entry-level customer acquisition pipeline and requires proactive positioning."
                ),
                "recommended_action": (
                    "Audit our feature tier gating, emphasize superior reliability and included support, "
                    "and prepare a targeted counter-battlecard for sales leads."
                )
            }
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=json.dumps(response_json)))])

        # Check if this is the Proposal Generator prompt
        elif "Proposal Generator" in last_message_content or "Synthesize the complete proposal" in last_message_content:
            quotes = re.findall(r'\* Quote: "(.*?)" \((.*?)\)', last_message_content)
            if not quotes:
                quotes = [(q, "https://verified-source.com") for q in re.findall(r'\* Quote: "(.*?)"', last_message_content)]

            evidence_items = []
            for q, src in quotes:
                evidence_items.append(f'> "{q}"\n*(Source: [{src}]({src}))*')
            evidence_md = "\n\n".join(evidence_items) if evidence_items else "Retained snapshot excerpts verify the competitor adjustments."

            proposal_md = (
                "# Strategic Counter-Proposal\n\n"
                "## 1. Problem / Opportunity\n"
                "Market dynamics have shifted due to competitor changes requiring an immediate response.\n\n"
                "## 2. Competitor Change\n"
                "Competitor adjusted pricing tiers and published updated features.\n\n"
                "## 3. Evidence\n"
                f"{evidence_md}\n\n"
                "## 4. Strategic Impact\n"
                "Pressure on entry-tier acquisition and customer retention.\n\n"
                "## 5. Proposed Response\n"
                "Deliver clear feature differentiation and update commercial packaging.\n\n"
                "## 6. Suggested Features/Work\n"
                "- Roll out automated workflow integrations.\n"
                "- Update sales enablement battlecards.\n\n"
                "## 7. Expected Value\n"
                "Preserve pipeline revenue and minimize churn risk.\n"
            )
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=proposal_md))])

        # Generic fallback
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="{}"))])

    @property
    def _llm_type(self) -> str:
        return "mock-deterministic"


class LLMProviderFactory:
    """
    Factory for instantiating free/open-source LLM adapters.
    Complies with zero-paid-API mandate using Groq, Gemini Free Tier, Ollama, or Mock fallback.
    """
    @staticmethod
    def get_chat_model() -> BaseChatModel:
        provider = (getattr(settings, "LLM_PROVIDER", None) or "mock").lower()

        try:
            if provider == "groq" and getattr(settings, "GROQ_API_KEY", None):
                from langchain_groq import ChatGroq
                return ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model_name=getattr(settings, "LLM_MODEL_NAME", None) or "llama-3.3-70b-versatile",
                    temperature=0.1
                )

            elif provider == "gemini" and getattr(settings, "GEMINI_API_KEY", None):
                from langchain_google_genai import ChatGoogleGenerativeAI
                model_name = settings.LLM_MODEL_NAME if "gemini" in settings.LLM_MODEL_NAME else "gemini-1.5-flash"
                return ChatGoogleGenerativeAI(
                    google_api_key=settings.GEMINI_API_KEY,
                    model=model_name,
                    temperature=0.1
                )

            elif provider == "ollama":
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(
                    base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
                    model=getattr(settings, "LLM_MODEL_NAME", None) or "llama3.2",
                    temperature=0.1
                )

        except Exception as exc:
            logger.warning(
                "Failed to initialize provider '%s' (%s). Falling back to deterministic offline adapter.",
                provider, exc
            )

        # Default fallback to deterministic offline model
        return MockDeterministicChatModel()
