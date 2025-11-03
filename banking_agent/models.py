from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class AgentResponse(BaseModel):
    voice_str: str = Field(..., description="Natural, conversational text to be spoken aloud answering the main themes of user query. Keep it concise and easy to understand when heard and under 30 words.")
    text: str = Field(..., description="Well-structured markdown formatted text from the Document Knowledge Base that answers the user query in detail. This text is displayed in the UI and should include proper markdown formatting with headings (##, ###), bullet points, numbered lists, and other formatting that enhances readability and organization. Structure key points clearly with appropriate hierarchy and emphasis. Only text from the relevant source no additional commentary.")
    send_to_ui: bool = Field(..., description="Whether to display the text field in the UI.")
    follow_up_questions: List[str] = Field(default_factory=list, description="A list of 2-4 follow-up questions related to the user query that might help continue the conversation. These questions should be directly related to the topic and encourage deeper exploration.")


class ValidationResult(BaseModel):
    """Output schema for response validation agent."""

    is_valid: bool = Field(
        ...,
        description="True if response passes all validation checks, False otherwise. This is the final verdict on whether the response meets quality standards."
    )

    traceability_check: bool = Field(
        ...,
        description="True if all response content (voice_str and text) is grounded in RAG tool output OR if the intent type does not require RAG grounding (e.g., greetings, general questions about agent capabilities). False if any fabrication, hallucination, or use of pre-trained knowledge beyond the RAG results is detected when RAG grounding IS required."
    )

    consistency_check: bool = Field(
        ...,
        description="True if voice_str and text fields are semantically consistent, meaning they convey the same core information with text elaborating on voice. False if contradictions, different topics, or inconsistent facts are present."
    )

    tool_usage_check: Optional[bool] = Field(
        default=None,
        description="Optional check for whether RAG tool usage requirement was met. True if tool was called when required (investment_related intent), True if tool was NOT called when not required (greet, general_question), False if tool usage does not match intent requirements. None if not applicable."
    )

    validation_mode: Optional[str] = Field(
        default=None,
        description="Optional field tracking which validation mode was applied based on user intent: 'greet', 'general_question', 'investment_related_question', or 'out_of_scope'. Helps with debugging and transparency."
    )

    feedback: str = Field(
        default="",
        description="Specific, actionable feedback on what needs improvement. Empty string if valid. Must be detailed and point to exact issues, such as: 'voice_str mentions dividend yield of 3.5% but this number does not appear in RAG output' or 'text discusses tax implications while voice discusses diversification - inconsistent topics'."
    )

    escalate: bool = Field(
        ...,
        description="True if validation passed and loop should exit. False to continue retry loop. This flag controls the LoopAgent behavior."
    )


class IntentCategory(str, Enum):
    """Intent categories for user messages."""
    GREET = "greet"
    INVESTMENT_RELATED = "investment_related_question"
    GENERAL_QUESTION = "general_question"
    OUT_OF_SCOPE = "out_of_scope"


class IntentGuardrailOutput(BaseModel):
    """Output schema for intent guardrail checks."""
    query: str = Field(..., description="The original user message that was classified. This field is included for reference and to provide context for the intent classification.")
    intent: IntentCategory = Field(..., description="The classified intent category of the user message. Must be one of the defined IntentCategory enum values: GREET, INVESTMENT_RELATED, GENERAL_QUESTION, or OUT_OF_SCOPE. This classification determines how the message will be processed or downstream components.")
    reasoning: str = Field(..., description="Detailed explanation of why this intent was chosen over others. Include specific phrases or keywords from the user message that influenced the decision, and how priority rules were applied if multiple intents were present. This field helps with transparency and debugging intent classification.")
    confidence: float = Field(..., description="Numeric value between 0.0 and 1.0 representing the model's confidence in the intent classification. Higher values (closer to 1.0) indicate stronger confidence. Values below 0.7 might warrant additional validation or clarification from the user.")
    allowed: bool = Field(..., description="Boolean flag indicating whether this intent should be allowed to proceed to downstream processing. Should be set to false ONLY for OUT_OF_SCOPE intents that violate usage policies or request information outside the system's capabilities.")
