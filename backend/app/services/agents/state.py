from typing import TypedDict, List, Dict, Any, Optional


class GroundedQuote(TypedDict):
    verbatim_quote: str
    char_offset_start: Optional[int]
    char_offset_end: Optional[int]
    source_url: str


class AgentState(TypedDict, total=False):
    # Context & Inputs
    workspace_id: str
    candidate_diff_id: str
    change_id: str
    snapshot_id: str
    source_url: str
    source_type: str
    competitor_name: str
    
    # Workspace Product Context
    product_name: str
    value_proposition: str
    target_audience: str
    pricing_summary: str
    strategic_focus: str
    
    # Ingestion Artifacts
    candidate_diff: str
    snapshot_text: str

    # Node 1: Context Researcher Outputs
    factual_summary: str
    extracted_quotes: List[str]

    # Node 2: Impact Analyzer Outputs
    title: str
    category: str
    impact_analysis: str
    recommended_action: str

    # Node 3: Critic / Verifier Outputs
    verified_quotes: List[GroundedQuote]
    unsupported_claims: List[str]
    critic_notes: str
    grounding_score: float  # EGA Percentage: 0.0 to 100.0
    confidence_level: str   # "HIGH", "MEDIUM", "LOW"
    verification_status: str # "VERIFIED", "DOWNGRADED", "REJECTED"

    # Execution control & feedback loops
    iteration: int
    max_iterations: int
    next_step: str
