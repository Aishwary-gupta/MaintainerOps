from maintainerops.ai import AIEnrichmentProvider


def test_ai_offline_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MAINTAINEROPS_AI_PROVIDER", "auto")

    ai = AIEnrichmentProvider()
    assert ai.is_available() is False

    original = "Hi @alice, please provide reproduction steps."
    refined = ai.refine_draft(original, "Crash on startup", "Body text")
    assert refined == original

    summary = ai.summarize_thread(["Comment 1", "Comment 2"])
    assert summary is None


def test_ai_refine_draft_mocked(monkeypatch):
    ai = AIEnrichmentProvider(provider="gemini")
    monkeypatch.setattr(ai, "is_available", lambda: True)
    monkeypatch.setattr(
        ai,
        "_call_ai",
        lambda prompt: "Hi @alice! Could you kindly share your reproduction steps? We appreciate your help!",
    )

    refined = ai.refine_draft("Original draft", "Crash", "Body")
    assert "Could you kindly share" in refined


def test_ai_summarize_thread_mocked(monkeypatch):
    ai = AIEnrichmentProvider(provider="openai")
    monkeypatch.setattr(ai, "is_available", lambda: True)
    monkeypatch.setattr(
        ai,
        "_call_ai",
        lambda prompt: "1. Memory leak observed on workers\n2. Workaround available in v2\n3. Patch pending review",
    )

    bullets = ai.summarize_thread(["Many comments..."])
    assert bullets is not None
    assert len(bullets) == 3
    assert "Memory leak observed" in bullets[0]
