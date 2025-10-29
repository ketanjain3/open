from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class AgentResponse(BaseModel):
    voice_str: str = Field(..., description="Natural, conversational text to be spoken aloud answering the main themes of user query. Keep it concise and easy to understand when heard and under 30 words.")
    text: str = Field(..., description="Well-structured markdown formatted text from the Document Knowledge Base that answers the user query in detail. This text is displayed in the UI and should include proper markdown formatting with headings (##, ###), bullet points, numbered lists, and other formatting that enhances readability and organization. Structure key points clearly with appropriate hierarchy and emphasis. Only text from the relevant source no additional commentary.")
    send_to_ui: bool = Field(..., description="Whether to display the text field in the UI.")
    follow_up_questions: List[str] = Field(default_factory=list, description="A list of 2-4 follow-up questions related to the user query that might help continue the conversation. These questions should be directly related to the topic and encourage deeper exploration.")


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
    confidence_float: float = Field(..., description="Numeric value between 0.0 and 1.0 representing the model's confidence in the intent classification. Higher values (closer to 1.0) indicate stronger confidence. Values below 0.7 might warrant additional validation or clarification from the user.")
    allowed: bool = Field(..., description="Boolean flag indicating whether this intent should be allowed to proceed to downstream processing. Should be set to false ONLY for OUT_OF_SCOPE intents that violate usage policies or request information outside the system's capabilities.")
