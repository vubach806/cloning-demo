"""Pydantic models for agent inputs and outputs."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class IntentAgentInput(BaseModel):
    """Input model for Intent Agent."""

    user_id: str = Field(description="User identifier")
    session_id: str = Field(default="", description="Session identifier")
    raw_message: str = Field(description="Raw user message")
    language: str = Field(default="vi", description="Language code")


class IntentAgentOutput(BaseModel):
    """Output model for Intent Agent."""

    user_id: str = Field(description="User identifier")
    session_name: str = Field(default="", description="Session name")
    clean_intent_text: str = Field(description="Cleaned and clarified intent text")
    intent_code: str = Field(description="Intent classification code")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")


class AnalyseHandoffInput(BaseModel):
    """Input model for Analyse Handoff Agent."""

    user_id: str = Field(description="User identifier")
    session_id: str = Field(default="", description="Session identifier")
    raw_message: str = Field(description="Raw user message")
    language: str = Field(default="vi", description="Language code")


class PolicyFlags(BaseModel):
    """Policy flags for handoff analysis."""

    legal: bool = Field(default=False, description="Legal concerns flag")
    medical: bool = Field(default=False, description="Medical concerns flag")
    financial_risk: bool = Field(default=False, description="Financial risk flag")
    high_technical: bool = Field(default=False, description="High technical complexity flag")


class EmotionScore(BaseModel):
    """Emotion scores detected from user message."""

    frustration: float = Field(default=0.0, ge=0.0, le=1.0, description="Frustration level")
    anger: float = Field(default=0.0, ge=0.0, le=1.0, description="Anger level")
    sadness: float = Field(default=0.0, ge=0.0, le=1.0, description="Sadness level")
    joy: float = Field(default=0.0, ge=0.0, le=1.0, description="Joy level")
    fear: float = Field(default=0.0, ge=0.0, le=1.0, description="Fear level")
    neutral: float = Field(default=0.0, ge=0.0, le=1.0, description="Neutral level")


class AnalyseHandoffOutput(BaseModel):
    """Output model for Analyse Handoff Agent."""

    user_id: str = Field(description="User identifier")
    policy_flags: PolicyFlags = Field(description="Policy concern flags")
    emotion_score: EmotionScore = Field(description="Detected emotion scores")
    handoff_required: bool = Field(description="Whether human handoff is required")
    handoff_reason: Optional[str] = Field(None, description="Reason for handoff if required")
    risk_level: str = Field(description="Risk level: low, medium, high")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")


class OrchestratorAgentInput(BaseModel):
    """Input model for Orchestrator Agent."""

    user_id: str = Field(description="User identifier")
    clean_intent_text: str = Field(description="Cleaned intent text from Intent Agent")
    intent_code: str = Field(description="Intent code from Intent Agent")
    policy_flags: PolicyFlags = Field(description="Policy flags from Analyse Handoff")
    emotion_score: EmotionScore = Field(description="Emotion scores from Analyse Handoff")
    handoff_required: bool = Field(description="Whether handoff is required")
    handoff_reason: Optional[str] = Field(None, description="Handoff reason if required")
    risk_level: str = Field(description="Risk level from Analyse Handoff")


class OrchestratorAgentOutput(BaseModel):
    """Output model for Orchestrator Agent."""

    user_id: str = Field(description="User identifier")
    task: str = Field(description="Task type: 'sales_task' or 'human_handle'")
    clean_intent_text: str = Field(description="Cleaned intent text")
    intent_code: str = Field(description="Intent code")
    policy_flags: PolicyFlags = Field(description="Policy flags")
    emotion_score: EmotionScore = Field(description="Emotion scores")
    handoff_required: bool = Field(description="Whether handoff is required")
    handoff_reason: Optional[str] = Field(None, description="Handoff reason if required")
    risk_level: str = Field(description="Risk level")
    task_reason: Optional[str] = Field(None, description="Reason for task selection")


# Predict Customer Requirement Agent Models
class PredictRequirementInput(BaseModel):
    """Input model for Predict Customer Requirement Agent."""

    latest_message: str = Field(description="Latest user message")
    short_memory: list = Field(
        default_factory=list,
        description="Recent conversation history (20 most recent segments from Conversation Buffer)",
    )
    sales_node: str = Field(description="Current sales node/stage")


class PredictRequirementOutput(BaseModel):
    """Output model for Predict Customer Requirement Agent."""

    explicit_requirements: list[str] = Field(
        description="Explicitly stated or clearly inferred requirements"
    )
    implicit_requirements: list[str] = Field(
        description="Implicitly inferred requirements not explicitly stated"
    )
    service_type: str = Field(
        description="Type of service: product_purchase, consultation, support, etc."
    )


# Classify Step Agent Models
class SalesGraph(BaseModel):
    """Sales graph structure."""

    nodes: list[str] = Field(description="List of available sales nodes/stages")
    current_node: str = Field(description="Current sales node")


class ClassifyStepInput(BaseModel):
    """Input model for Classify Step Agent."""

    clean_intent_text: str = Field(description="Cleaned and clarified intent text")
    sales_graph: SalesGraph = Field(description="Sales graph with nodes and current node")


class ClassifyStepOutput(BaseModel):
    """Output model for Classify Step Agent."""

    current_sales_node: str = Field(description="Classified current sales node")
    allowed_next_nodes: list[str] = Field(description="List of allowed next nodes")
    reason: Optional[str] = Field(None, description="Reason for classification")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")


# Profile Agent Models
class HistoricalData(BaseModel):
    """Historical customer data."""

    total_orders: int = Field(default=0, description="Total number of orders")
    total_spend: float = Field(default=0.0, description="Total amount spent")
    last_purchase_days: int = Field(default=0, description="Days since last purchase")


class ProfileAgentInput(BaseModel):
    """Input model for Profile Agent."""

    user_id: str = Field(description="User identifier")
    historical_data: HistoricalData = Field(description="Historical customer data")
    label_definitions: list[str] = Field(
        description="List of available customer labels (e.g., 'VIP', 'tiềm năng', 'bình thường')"
    )


class ProfileAgentOutput(BaseModel):
    """Output model for Profile Agent."""

    customer_label: str = Field(description="Assigned customer label")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    priority_score: int = Field(ge=0, description="Priority score (higher = more priority)")


# Up Sales / Cross Sales Agent Models
class Requirements(BaseModel):
    """Customer requirements structure."""

    explicit: list[str] = Field(default_factory=list, description="Explicit requirements")
    implicit: list[str] = Field(default_factory=list, description="Implicit requirements")


class ProductCombo(BaseModel):
    """Product combo structure."""

    combo_id: str = Field(description="Combo identifier")
    products: list[str] = Field(description="List of products in the combo")
    stock: int = Field(ge=0, description="Available stock quantity")
    price: float = Field(ge=0.0, description="Price of the combo in VND")


class UpSalesCrossSalesInput(BaseModel):
    """Input model for Up Sales / Cross Sales Agent."""

    requirements: Requirements = Field(description="Customer requirements (explicit and implicit)")
    available_combos: list[ProductCombo] = Field(description="Available product combos with stock")
    short_memory: list = Field(
        default_factory=list,
        description="Recent conversation history (20 most recent segments from Conversation Buffer)",
    )
    summary_conversation: Optional[str] = Field(
        None, description="Conversation summary from PostgreSQL Sessions Summary"
    )


class UpSalesCrossSalesOutput(BaseModel):
    """Output model for Up Sales / Cross Sales Agent."""

    selected_combo: Optional[str] = Field(None, description="Selected combo ID")
    reason: Optional[str] = Field(None, description="Reason for combo selection")
    response_text: str = Field(
        default="", description="Response text (usually empty, used by Sales Agent)"
    )


# Sales Agent Models
class SalesAgentInput(BaseModel):
    """Input model for Sales Agent."""

    customer_label: str = Field(description="Customer label (e.g., VIP, tiềm năng, bình thường)")
    sales_node: str = Field(description="Current sales node/stage")
    requirements: Requirements = Field(description="Customer requirements (explicit and implicit)")
    selected_combo: Optional[ProductCombo] = Field(
        None, description="Selected combo details (id/products/stock/price)"
    )
    debug_prompt: Optional[str] = Field(
        default=None,
        description="(debug) Exact prompt that will be sent to the LLM",
    )
    tone_policy: str = Field(
        default="professional_warm",
        description="Tone policy for response (e.g., professional_warm, friendly, formal)",
    )
    short_memory: list = Field(
        default_factory=list,
        description="Recent conversation history (20 most recent segments from Conversation Buffer)",
    )


class SalesAgentOutput(BaseModel):
    """Output model for Sales Agent."""

    response_text: str = Field(description="Response text to be delivered to the user")
    next_expected_input: str = Field(
        description="Expected type of next user input (e.g., preference_clarification, price_inquiry)"
    )
    stay_in_sales_node: bool = Field(
        default=True, description="Whether to stay in the current sales node"
    )


# Guardrail Agent Models
class GuardrailInput(BaseModel):
    """Input model for Guardrail Agent."""

    response_text: str = Field(description="Response text to be validated/modified")
    product_data: Optional[list] = Field(None, description="Product data for validation (optional)")


class GuardrailOutput(BaseModel):
    """Output model for Guardrail Agent."""

    approved: bool = Field(description="Whether the content is approved")
    modified_text: Optional[str] = Field(
        None, description="Modified text if changes were made (null if no changes)"
    )
    sales_doublecheck: bool = Field(
        default=False, description="Whether sales content needs double-check"
    )
    reason_recheck: Optional[str] = Field(None, description="Reason for recheck if required")
