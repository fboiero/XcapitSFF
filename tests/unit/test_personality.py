"""Tests for assistant personality."""

from xcapitsff.assistant.personality import (
    DEFAULT_PERSONALITY,
    get_ack,
    get_error,
    get_greeting,
    get_help,
    get_transition,
)


def test_default_personality():
    assert DEFAULT_PERSONALITY.name == "Sofi"
    assert DEFAULT_PERSONALITY.use_vos is True
    assert DEFAULT_PERSONALITY.language == "es_latam"


def test_greeting_new_user():
    greeting = get_greeting(is_returning=False)
    assert "Sofi" in greeting
    assert len(greeting) > 10


def test_greeting_returning():
    greeting = get_greeting(is_returning=True)
    assert len(greeting) > 10


def test_ack_positive():
    ack = get_ack("positive")
    assert len(ack) > 0


def test_ack_created():
    ack = get_ack("created")
    assert len(ack) > 0


def test_ack_working():
    ack = get_ack("working")
    assert len(ack) > 0


def test_error_not_found():
    err = get_error("not_found")
    assert len(err) > 10


def test_error_unknown():
    err = get_error("unknown")
    assert "entendí" in err.lower() or "probá" in err.lower() or "ayuda" in err.lower()


def test_transition_after_create_lead():
    transitions = get_transition("after_create_lead")
    assert len(transitions) >= 2


def test_transition_after_dashboard():
    transitions = get_transition("after_dashboard")
    assert len(transitions) >= 2


def test_transition_unknown_context():
    transitions = get_transition("nonexistent")
    assert transitions == []


def test_help_text():
    help_text = get_help()
    assert "Ventas" in help_text
    assert "Soporte" in help_text
    assert "Analytics" in help_text
    assert "Ctrl+K" in help_text
