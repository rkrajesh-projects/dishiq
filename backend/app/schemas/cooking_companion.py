from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CompanionMessage(BaseModel):
    role: str = Field(..., description="Role of the sender ('user' or 'assistant')")
    content: str = Field(..., description="Message text")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("user", "assistant", "system"):
            raise ValueError("Role must be 'user' or 'assistant'")
        return v_clean


class CompanionChatRequest(BaseModel):
    cooking_session_id: str = Field(..., description="ID of the active cooking session")
    message: str = Field(..., description="User's cooking question")
    step_index: Optional[int] = Field(None, ge=0, description="Current step index (0-based)")
    conversation_history: Optional[List[CompanionMessage]] = Field(
        default=[], description="Recent conversation turns for context"
    )


class CompanionChatResponse(BaseModel):
    reply: str
    response_mode: str = Field(
        ...,
        description="Whether response was produced by an external LLM ('llm') or rule-based engine ('deterministic_fallback')",
    )
    provider: Optional[str] = None
    model: Optional[str] = None
    suggested_actions: List[str] = []
    related_step: Optional[int] = None
    disclaimer: str = "AI suggestions are supplementary. Stored recipe instructions remain authoritative."
