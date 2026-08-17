"""translate_cached — caching, failure -> None (never raises), and
provenance fields. Uses a fake TranslationProvider, no real DeepL call."""
from __future__ import annotations

from src.data_access.translation.interfaces import TranslationConfigError
from src.data_access.translation.translation_service import translate_cached
from src.models.models import Translation


class _FakeProvider:
    name = "DeepL"

    def __init__(self, result: str | None = None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.call_count = 0

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        self.call_count += 1
        if self._error:
            raise self._error
        return self._result


def test_successful_translation_returns_translation_with_provenance(tmp_path):
    provider = _FakeProvider(result="New facility investment, etc.")

    result = translate_cached(provider, "20260807000537", "신규시설투자등", tmp_path)

    assert isinstance(result, Translation)
    assert result.translated_text == "New facility investment, etc."
    assert result.provider == "DeepL"
    assert result.source_lang == "ko"
    assert result.target_lang == "en"
    assert result.translated_at


def test_second_call_with_same_document_and_text_hits_cache_not_provider(tmp_path):
    provider = _FakeProvider(result="translated")

    translate_cached(provider, "doc1", "신규시설투자등", tmp_path)
    translate_cached(provider, "doc1", "신규시설투자등", tmp_path)

    assert provider.call_count == 1


def test_same_text_different_document_id_are_cached_separately(tmp_path):
    provider = _FakeProvider(result="translated")

    translate_cached(provider, "doc1", "동일한텍스트", tmp_path)
    translate_cached(provider, "doc2", "동일한텍스트", tmp_path)

    assert provider.call_count == 2


def test_different_text_same_document_id_are_cached_separately(tmp_path):
    provider = _FakeProvider(result="translated")

    translate_cached(provider, "doc1", "텍스트A", tmp_path)
    translate_cached(provider, "doc1", "텍스트B", tmp_path)

    assert provider.call_count == 2


def test_provider_failure_returns_none_not_an_exception(tmp_path):
    provider = _FakeProvider(error=TranslationConfigError("no key"))

    result = translate_cached(provider, "doc1", "text", tmp_path)

    assert result is None


def test_empty_text_returns_none_without_calling_provider(tmp_path):
    provider = _FakeProvider(result="should not be called")

    result = translate_cached(provider, "doc1", "", tmp_path)

    assert result is None
    assert provider.call_count == 0


def test_failed_translation_is_not_cached_so_a_retry_can_succeed_later(tmp_path):
    failing_provider = _FakeProvider(error=TranslationConfigError("no key"))
    translate_cached(failing_provider, "doc1", "text", tmp_path)

    working_provider = _FakeProvider(result="now it works")
    result = translate_cached(working_provider, "doc1", "text", tmp_path)

    assert result is not None
    assert result.translated_text == "now it works"
