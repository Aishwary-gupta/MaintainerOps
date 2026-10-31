import json
import os
from typing import Any, Dict, List, Optional
import httpx


class AIEnrichmentProvider:
    """Optional pluggable semantic AI helper for summarizing long threads and refining maintainer tone."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or os.getenv("MAINTAINEROPS_AI_PROVIDER") or "auto").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def is_available(self) -> bool:
        """Returns True if any supported AI backend credentials or endpoints are available."""
        if self.provider == "gemini" and self.gemini_key:
            return True
        if self.provider == "openai" and self.openai_key:
            return True
        if self.provider == "ollama":
            return True
        if self.provider == "auto":
            return bool(self.gemini_key or self.openai_key)
        return False

    def summarize_thread(self, comments: List[str], max_bullets: int = 3) -> Optional[List[str]]:
        """Summarizes multiple lengthy discussion comments into crisp bullet points."""
        if not comments or not self.is_available():
            return None

        joined = "\n\n---\n\n".join(comments[:15])
        prompt = (
            f"You are an open source maintainer assistant. Summarize the following issue thread into "
            f"at most {max_bullets} objective, factual bullet points focusing on key findings, blockers, and next steps.\n\n"
            f"Comments:\n{joined}"
        )

        res = self._call_ai(prompt)
        if not res:
            return None

        lines = [line.strip().lstrip("-*•123456789. ") for line in res.splitlines() if line.strip()]
        return lines[:max_bullets]

    def refine_draft(
        self,
        original_draft: str,
        issue_title: str,
        issue_body: str,
        tone: str = "polite_collaborative",
    ) -> str:
        """Polishes a deterministic draft message to match the repository's desired tone."""
        if not self.is_available() or not original_draft:
            return original_draft

        prompt = (
            f"You are MaintainerOps, a human-first triage assistant. Refine the draft response below.\n"
            f"Tone: {tone} (empathetic, concise, professional, appreciative of the contributor's time).\n"
            f"Context Title: {issue_title}\n"
            f"Original Draft: {original_draft}\n\n"
            f"Instructions: Return ONLY the refined comment text with zero meta-commentary, markdown backticks, or greetings other than the comment itself."
        )

        refined = self._call_ai(prompt)
        return refined.strip() if refined else original_draft

    def _call_ai(self, prompt: str) -> Optional[str]:
        try:
            # 1. Gemini
            if (self.provider in ["gemini", "auto"]) and self.gemini_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
                }
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()

            # 2. OpenAI
            if (self.provider in ["openai", "auto"]) and self.openai_key:
                base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                url = f"{base_url.rstrip('/')}/chat/completions"
                payload = {
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 400,
                }
                headers = {"Authorization": f"Bearer {self.openai_key}"}
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()

            # 3. Ollama
            if self.provider == "ollama":
                url = f"{self.ollama_host.rstrip('/')}/api/generate"
                payload = {
                    "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
                    "prompt": prompt,
                    "stream": False,
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        return resp.json().get("response", "").strip()

        except Exception:
            return None

        return None
