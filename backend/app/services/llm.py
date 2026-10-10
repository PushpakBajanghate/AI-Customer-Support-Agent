"""LLM Service Layer for AI Customer Support Agent.

Connects to Google Gemini dynamically at runtime using credentials from .env.
Ensures zero hardcoded responses, fake fallbacks, or mock scripts.
"""

import time
from fastapi import HTTPException, status
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings

# System prompt defining assistant role and safety rules
SYSTEM_PROMPT = (
    "You are an AI customer-support assistant that helps authenticated customers "
    "with orders, returns, refunds, shipping and product questions.\n\n"
    "Guidelines:\n"
    "- Be concise.\n"
    "- Be helpful.\n"
    "- Never invent order information.\n"
    "- Never claim an action was performed unless verified.\n"
    "- Ask for clarification when necessary."
)

def get_llm(model_override: str | None = None, timeout: int = 15):
    """Initializes and returns the configured Google Gemini LLM client."""
    api_key = settings.LLM_API_KEY.strip() if settings.LLM_API_KEY else ""
    model_name = (model_override or settings.LLM_MODEL).strip()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM configuration error: LLM_API_KEY is not configured in .env."
        )

    if not model_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM configuration error: LLM_MODEL is not configured in .env."
        )

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        timeout=timeout,
        max_retries=1,
    )

def _extract_content_text(content) -> str:
    """Helper to extract clean string content from response blocks or string."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return " ".join(parts).strip()
    return str(content).strip()

def generate_support_response(user_message: str) -> str:
    """
    Sends the user's actual runtime message and the system prompt to Google Gemini.
    Returns the real dynamically generated response from the LLM.
    Raises HTTPException if Gemini is unreachable or returns an error.
    """
    llm = get_llm()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    last_error = None
    for attempt in range(2):
        try:
            response = llm.invoke(messages)
            text_reply = _extract_content_text(response.content)
            if not text_reply:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Gemini API returned an empty response."
                )
            return text_reply
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc
            if "503" in str(exc) and attempt == 0:
                time.sleep(1.5)
                continue
            break

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Gemini API failure: {str(last_error)}"
    )
