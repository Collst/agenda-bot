"""
services/llm.py — Switchable LLM backend.

Set LLM_BACKEND=anthropic or LLM_BACKEND=ollama in .env.
All agent nodes call get_llm() rather than instantiating models directly,
so switching backends requires no code changes.
"""

import os
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv

load_dotenv()

def get_llm() -> BaseChatModel:
    """
    Return a LangChain chat model based on LLM_BACKEND env var.

    anthropic → ChatAnthropic (cloud, higher quality)
    ollama    → ChatOllama    (local, data stays on-device)
    """
    backend = os.getenv("LLM_BACKEND", "anthropic").lower().strip()

    if backend == "anthropic":
        # Import lazily so the package is only required when used
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.2,
        )

    if backend == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.2,
        )
    
    if backend == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2,
        )

    raise ValueError(
        f"Unknown LLM_BACKEND '{backend}'. "
        "Set LLM_BACKEND to 'anthropic', 'ollama', or 'gemini'."
    )
