"""LLM drafting with explicit non-commercial and factual guardrails."""

from __future__ import annotations

import random
import re
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

from .config import Settings
from .filtering import commercial_flags
from .models import DraftResult, RawPost


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "optics_answer.md"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_user_prompt(post: RawPost, rules_text: str = "") -> str:
    body = (post.body or "").strip()
    if len(body) > 8000:
        body = body[:8000] + "\n[truncated for review]"
    rules = rules_text.strip() or "(subreddit rules were not fetched; check them before posting)"
    return (
        f"Subreddit: r/{post.subreddit}\n"
        f"Permalink: {post.permalink}\n"
        f"Title: {post.title}\n\n"
        f"Post body:\n{body}\n\n"
        f"Subreddit rules:\n{rules}\n\n"
        "Draft a reply for a human to review and post. Follow the system rules exactly."
    )


def _extract_confidence(text: str) -> str:
    match = re.search(r"Confidence\s*:\s*(high|medium|low)", text, re.IGNORECASE)
    return match.group(1).lower() if match else "low"


def _extract_flags(text: str) -> list[str]:
    flags: list[str] = []
    match = re.search(r"Rule flags\s*:\s*(.+)", text, re.IGNORECASE)
    if match:
        raw = match.group(1).strip()
        if raw and raw.lower() not in {"none", "n/a", "-"}:
            flags.extend(part.strip() for part in re.split(r"[,;]", raw) if part.strip())
    return flags


def postprocess_draft(result: DraftResult) -> DraftResult:
    flags = list(dict.fromkeys(result.flags))
    flags.extend(commercial_flags(result.text))
    if len(result.text.strip()) < 120:
        flags.append("draft_too_short")
    if "as an ai" in result.text.lower():
        flags.append("ai_self_reference")
    confidence = result.confidence.lower()
    if flags and confidence == "high":
        confidence = "medium"
    return DraftResult(
        text=result.text,
        confidence=confidence,
        flags=list(dict.fromkeys(flags)),
        model=result.model,
    )


class TemplateProvider:
    """Offline placeholder used for tests and when no LLM key is configured."""

    def draft(self, post: RawPost, rules_text: str = "") -> DraftResult:
        text = (
            "Answer draft\n"
            "Write the technical answer here after reading the post and checking the sources.\n\n"
            "Key assumptions\n"
            "- Add the assumptions you had to make.\n\n"
            "Sources\n"
            "- Add public standard/textbook references, or write 'general practice - verify'.\n\n"
            "Verification checklist\n"
            "- Verify every tolerance, coating, and standard claim.\n"
            "- Confirm no company name, price, lead time, or sales language.\n"
            "- Confirm the answer follows r/Optics rules.\n\n"
            "Confidence: low\n"
            "Rule flags: llm_disabled"
        )
        return DraftResult(text=text, confidence="low", flags=["llm_disabled"], model="template")


class LLMProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.llm_configured:
            raise ValueError("LLM_API_KEY is not configured")
        self.settings = settings
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def draft(self, post: RawPost, rules_text: str = "") -> DraftResult:
        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.2,
            "max_tokens": 1000,
            "messages": [
                {"role": "system", "content": load_system_prompt()},
                {"role": "user", "content": build_user_prompt(post, rules_text)},
            ],
        }
        if not self.settings.llm_store:
            payload["store"] = False

        last_error: Exception | None = None
        for attempt in range(3):
            response = self.session.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "optics-qa-triage/0.1.0",
                },
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(random.uniform(0.5, 1.5))
                continue
            if response.status_code >= 400:
                last_error = RuntimeError(f"LLM HTTP {response.status_code}: {response.text[:300]}")
                break
            data = response.json()
            choices = data.get("choices", [])
            content = ""
            if choices:
                content = str(choices[0].get("message", {}).get("content", "") or "")
            if not content.strip():
                last_error = RuntimeError("LLM returned an empty draft")
                break
            result = DraftResult(
                text=content.strip(),
                confidence=_extract_confidence(content),
                flags=_extract_flags(content),
                model=str(data.get("model", self.settings.llm_model)),
            )
            return postprocess_draft(result)
        raise RuntimeError(f"LLM drafting failed: {last_error}")


def make_provider(settings: Settings, no_llm: bool = False) -> LLMProvider | TemplateProvider:
    if no_llm or not settings.llm_configured:
        return TemplateProvider()
    return LLMProvider(settings)
