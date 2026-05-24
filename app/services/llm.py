"""
LLM Service with multi-key Groq rotation and OpenRouter fallback.

Fallback chain per call:
  For each model in priority order:
    → Try Groq key 1  (no SDK retries — we control fallback)
    → Try Groq key 2
    → Try OpenRouter equivalent
  If all models exhausted → raise RuntimeError
"""

import json
import time
import logging
from typing import Type, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel
from groq import Groq
import httpx

from app.utils.config import GROQ_API_KEYS, OPENROUTER_API_KEY, logger

T = TypeVar("T", bound=BaseModel)

# ── Model lists ───────────────────────────────────────────────────────────────
GROQ_MODELS_PRIORITY = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

OPENROUTER_MODELS_PRIORITY = [
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mixtral-8x7b-instruct",
    "google/gemma-2-9b-it",
]

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODEL_MAP = {
    "llama-3.3-70b-versatile": "meta-llama/llama-3.3-70b-instruct",
    "llama-3.1-8b-instant": "meta-llama/llama-3.1-8b-instruct",
    "mixtral-8x7b-32768": "mistralai/mixtral-8x7b-instruct",
    "gemma2-9b-it": "google/gemma-2-9b-it",
}


def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return "429" in s or "rate_limit" in s or "rate limit" in s or "quota" in s or "too many" in s


class LLMService:
    def __init__(self):
        # max_retries=0 disables the Groq SDK's internal retry loop so OUR
        # fallback chain fires immediately on a 429.
        self._groq_clients: List[Groq] = []
        for key in GROQ_API_KEYS:
            try:
                self._groq_clients.append(Groq(api_key=key, max_retries=0))
            except Exception as e:
                logger.warning(f"Failed to initialise Groq client: {e}")

        if not self._groq_clients and not OPENROUTER_API_KEY:
            raise ValueError(
                "No LLM provider available. Set GROQ_API_KEY or OPENROUTER_API_KEY."
            )

        self.default_model = "llama-3.3-70b-versatile"
        self.fast_model = "llama-3.1-8b-instant"

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _call_groq(
        self,
        client: Groq,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
    ) -> str:
        kwargs: Dict[str, Any] = dict(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _call_openrouter(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
    ) -> str:
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not configured.")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://research-platform.local",
            "X-Title": "AI Research Platform",
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(OPENROUTER_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] or ""

    # ── Public API ────────────────────────────────────────────────────────────

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Fallback chain — for each model, tries every key before moving on:

          model_1 → Groq key1 → Groq key2 → OpenRouter
          model_2 → Groq key1 → Groq key2 → OpenRouter
          ...
        """
        model_name = model or self.default_model
        models_to_try = [model_name] + [m for m in GROQ_MODELS_PRIORITY if m != model_name]

        for m in models_to_try:
            # ── Try each Groq key for this model ─────────────────────────────
            for client_idx, groq_client in enumerate(self._groq_clients):
                try:
                    logger.info(
                        f"[LLM] Groq key#{client_idx + 1} / model={m} | tokens={max_tokens}"
                    )
                    return self._call_groq(
                        groq_client, m, messages, temperature, max_tokens, response_format
                    )
                except Exception as e:
                    if _is_rate_limit(e):
                        logger.warning(
                            f"[LLM] Rate-limit: Groq key#{client_idx + 1} / {m}. "
                            f"{'Trying next key.' if client_idx + 1 < len(self._groq_clients) else 'No more keys — trying OpenRouter.'}"
                        )
                    else:
                        logger.error(f"[LLM] Groq key#{client_idx + 1} / {m} error: {e}")

            # ── Try OpenRouter for this model ─────────────────────────────────
            if OPENROUTER_API_KEY:
                or_model = OPENROUTER_MODEL_MAP.get(m, "meta-llama/llama-3.3-70b-instruct")
                try:
                    logger.info(f"[LLM] OpenRouter fallback / model={or_model}")
                    return self._call_openrouter(
                        or_model, messages, temperature, max_tokens, response_format
                    )
                except Exception as e:
                    logger.error(f"[LLM] OpenRouter / {or_model} error: {e}")

        raise RuntimeError(
            "All LLM providers and models exhausted. Check API keys and rate limits."
        )

    def complete_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 3000,
        retries: int = 2,
    ) -> T:
        """Call LLM demanding a JSON object conforming to the given Pydantic schema."""
        model_name = model or self.default_model
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_instructions = (
            f"\n\nYou MUST return a JSON object that conforms EXACTLY to this JSON Schema:\n"
            f"{schema_json}\n"
            "Do not include any pre-text, post-text, or markdown formatting tags. "
            "Return only valid raw JSON."
        )

        modified_messages: List[Dict[str, str]] = []
        has_system = False
        for msg in messages:
            if msg["role"] == "system":
                modified_messages.append(
                    {"role": "system", "content": msg["content"] + system_instructions}
                )
                has_system = True
            else:
                modified_messages.append(msg)

        if not has_system:
            modified_messages.insert(
                0,
                {
                    "role": "system",
                    "content": "You are a structured data generator." + system_instructions,
                },
            )

        for attempt in range(retries + 1):
            try:
                response_text = self.complete(
                    messages=modified_messages,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )

                cleaned = response_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3].strip()

                parsed = json.loads(cleaned)
                return schema.model_validate(parsed)

            except json.JSONDecodeError as jde:
                logger.warning(
                    f"[LLM] JSON decode failed (attempt {attempt + 1}/{retries + 1}): {jde}"
                )
                if attempt == retries:
                    raise ValueError(f"LLM failed to return valid JSON: {jde}")
            except Exception as e:
                logger.warning(
                    f"[LLM] Structured completion error (attempt {attempt + 1}/{retries + 1}): {e}"
                )
                if attempt == retries:
                    raise

        raise ValueError("Structured completion failed after all retries.")


# Singleton
llm_service = LLMService()
