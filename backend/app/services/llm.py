"""LLM Service Layer for AI Customer Support Agent.

Provides a modular, provider-agnostic interface for invoking language models.
Defaults to Google Gemini (configured via LLM_API_KEY and LLM_MODEL in .env).
"""

import os
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.models.customer import Customer

SYSTEM_PROMPT_TEMPLATE = """You are an AI customer-support assistant that helps authenticated customers with orders, returns, refunds, shipping and product questions.

Current Authenticated Customer Context:
- Customer Name: {customer_name}
- Customer ID: {customer_id}

Guidelines:
1. Be concise, polite, and helpful.
2. Never invent or hallucinate order numbers, shipping tracking numbers, or personal account details.
3. Never claim an action was performed (such as cancelling an order or issuing a refund) unless verified.
4. Ask for clarification when necessary.
5. In this foundation phase, politely address the customer by name, answer general support and policy questions, or inform them that transactional order tools will be available in upcoming phases.
"""

def get_llm():
    """Factory creating the configured LLM client instance (Google Gemini or OpenAI)."""
    provider = settings.LLM_PROVIDER.lower()
    api_key = settings.LLM_API_KEY
    model_name = settings.LLM_MODEL

    if not api_key or api_key.startswith("your_"):
        return None

    if provider in ["gemini", "google"]:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.3,
        )
    elif provider in ["openai"]:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or "gpt-4o-mini",
            api_key=api_key,
            temperature=0.3,
        )
    else:
        # Default fallback to Google Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.3,
        )

def generate_support_response(customer: Customer, user_message: str) -> str:
    """Sends customer message and system prompt to LLM and returns the generated reply."""
    llm = get_llm()

    if llm is None:
        # Graceful fallback when API key is not yet configured in .env
        return (
            f"Hello {customer.name}! I am your AI customer support assistant. "
            "I received your message: \"" + user_message + "\". "
            "(Notice: LLM_API_KEY is not configured yet in .env. "
            "Please add your Google Gemini API key to .env to activate live model responses.)"
        )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        customer_name=customer.name,
        customer_id=customer.id
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as exc:
        return (
            f"Hello {customer.name}, I encountered an issue connecting to the AI provider: {str(exc)}. "
            "Please check your API key and connection."
        )
