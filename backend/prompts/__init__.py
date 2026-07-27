"""
CevonDocs Versioned Invoice Extraction Prompts.
Exports system prompts and user templates across OpenAI, Gemini, and Groq providers.
"""
from backend.prompts.openai_invoice_prompt import OPENAI_SYSTEM_PROMPT, OPENAI_USER_PROMPT_TEMPLATE, OPENAI_PROMPT_VERSION
from backend.prompts.gemini_invoice_prompt import GEMINI_SYSTEM_PROMPT, GEMINI_USER_PROMPT_TEMPLATE, GEMINI_PROMPT_VERSION
from backend.prompts.groq_invoice_prompt import GROQ_SYSTEM_PROMPT, GROQ_USER_PROMPT_TEMPLATE, GROQ_PROMPT_VERSION

__all__ = [
    "OPENAI_SYSTEM_PROMPT", "OPENAI_USER_PROMPT_TEMPLATE", "OPENAI_PROMPT_VERSION",
    "GEMINI_SYSTEM_PROMPT", "GEMINI_USER_PROMPT_TEMPLATE", "GEMINI_PROMPT_VERSION",
    "GROQ_SYSTEM_PROMPT", "GROQ_USER_PROMPT_TEMPLATE", "GROQ_PROMPT_VERSION",
]
