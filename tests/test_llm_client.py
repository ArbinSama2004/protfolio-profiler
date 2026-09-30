import pytest
import requests

from profiler.llm import LLMError, client, extract_profile, parse_profile

GOOD = '{"name": "Jane Doe", "skills": ["Python"], "experience": [{"title": "Engineer", "company": "Acme"}]}'


def test_parse_plain_json():
    profile = parse_profile(GOOD)
    assert profile.name == "Jane Doe"
    assert profile.experience[0].company == "Acme"
    assert profile.email is None  # missing fields stay unknown, not invented


def test_parse_json_wrapped_in_markdown_and_prose():
    profile = parse_profile(f"Here you go:\n```json\n{GOOD}\n```")
    assert profile.name == "Jane Doe"


def test_null_lists_become_empty_lists():
    profile = parse_profile('{"name": "Jane", "skills": null, "projects": null}')
    assert profile.skills == [] and profile.projects == []


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse_profile("I could not find anything, sorry.")


def test_extract_profile_retries_once_after_bad_reply(monkeypatch):
    replies = iter(["not json at all", GOOD])
    calls = []

    def fake_chat(messages, model):
        calls.append(messages)
        return next(replies)

    monkeypatch.setattr(client, "_chat", fake_chat)
    assert extract_profile("some page text", "test-model").name == "Jane Doe"
    assert len(calls) == 2


def test_extract_profile_gives_up_after_two_bad_replies(monkeypatch):
    monkeypatch.setattr(client, "_chat", lambda messages, model: "still not json")
    with pytest.raises(LLMError):
        extract_profile("some page text", "test-model")


def test_unreachable_ollama_raises_llm_error(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(client.requests, "post", boom)
    with pytest.raises(LLMError, match="Could not reach Ollama"):
        extract_profile("some page text", "test-model")
