"""Tests fuer die KI-Stufe der Hilfe-Suche (ui/widgets/help_ai.py) - mit
simuliertem API-Client, ohne echte (kostenpflichtige) Aufrufe."""
import json
from types import SimpleNamespace

import pytest

from ui.widgets import help_ai


class FakeMessages:
    def __init__(self, payload, stop_reason="end_turn", usage=None):
        self.payload, self.stop_reason = payload, stop_reason
        self.usage = usage or SimpleNamespace(input_tokens=40, cache_creation_input_tokens=0,
                                              cache_read_input_tokens=7000, output_tokens=120)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="text", text=json.dumps(self.payload))],
            usage=self.usage)


def fake_client(payload, **kw):
    msgs = FakeMessages(payload, **kw)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


def test_request_shape_and_answer():
    client, msgs = fake_client({"answer": "In All Experiments ...", "entry_key": "all_experiments:tasks:0",
                                "confident": True})
    res = help_ai.ask("wo sehe ich alle aufträge einer maschine", "de", "key", client=client)
    assert res["entry_key"] == "all_experiments:tasks:0"
    call = msgs.calls[0]
    assert call["model"] == help_ai.MODEL
    assert call["fallbacks"] == "default" and help_ai.FALLBACK_BETA in call["betas"]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "[all_experiments:tasks:0]" in call["system"][0]["text"]
    schema = call["output_config"]["format"]["schema"]
    assert "none" in schema["properties"]["entry_key"]["enum"]
    assert call["output_config"]["effort"] == "low"
    # Kontingent: Cache-Lesungen zu 1/10
    assert res["usage"] == {"input": 40 + 700, "output": 120}


def test_unknown_key_becomes_none():
    client, _ = fake_client({"answer": "x", "entry_key": "does:not:exist", "confident": False})
    assert help_ai.ask("q", "en", "key", client=client)["entry_key"] == "none"


def test_refusal_returns_error():
    client, _ = fake_client({}, stop_reason="refusal")
    res = help_ai.ask("q", "en", "key", client=client)
    assert "error" in res and "usage" in res


def test_has_ai_access_follows_load_api_key(monkeypatch):
    import ui.advisor_worker as aw
    monkeypatch.setattr(aw, "load_api_key", lambda: None)
    assert help_ai.has_ai_access() is False
    monkeypatch.setattr(aw, "load_api_key", lambda: "sk-test")
    assert help_ai.has_ai_access() is True


@pytest.mark.parametrize("lang", ["en", "de", "es"])
def test_knowledge_complete_per_language(lang):
    kb = help_ai.build_knowledge(lang)
    assert len(kb["keys"]) == len(set(kb["keys"])) > 50
