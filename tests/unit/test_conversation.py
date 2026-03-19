"""Tests for conversation memory."""

from xcapitsff.agents.conversation import Conversation, ConversationMemory


def test_create_conversation():
    mem = ConversationMemory()
    conv = mem.create("sales_qualifier", "lead", context_id=42)
    assert conv.conversation_id.startswith("conv-")
    assert conv.agent_name == "sales_qualifier"
    assert conv.context_id == 42


def test_add_message():
    conv = Conversation(conversation_id="test", agent_name="test", context_type="test")
    conv.add_message("user", "Hello")
    conv.add_message("assistant", "Hi there")
    assert conv.message_count == 2


def test_get_messages_for_api():
    conv = Conversation(conversation_id="test", agent_name="test", context_type="test")
    conv.add_message("system", "You are a sales agent")
    conv.add_message("user", "Qualify this lead")
    conv.add_message("assistant", "Score: 75")

    api_msgs = conv.get_messages_for_api()
    assert len(api_msgs) == 2  # system excluded from API format
    assert api_msgs[0]["role"] == "user"


def test_get_messages_max_limit():
    conv = Conversation(conversation_id="test", agent_name="test", context_type="test")
    for i in range(30):
        conv.add_message("user", f"msg {i}")

    api_msgs = conv.get_messages_for_api(max_messages=5)
    assert len(api_msgs) == 5


def test_find_by_context():
    mem = ConversationMemory()
    mem.create("sales_qualifier", "lead", context_id=1)
    mem.create("outreach_composer", "lead", context_id=1)

    found = mem.find_by_context("sales_qualifier", "lead", 1)
    assert found is not None
    assert found.agent_name == "sales_qualifier"


def test_find_returns_none():
    mem = ConversationMemory()
    assert mem.find_by_context("unknown", "lead", 99) is None


def test_get_or_create_existing():
    mem = ConversationMemory()
    conv1 = mem.get_or_create("agent", "lead", 1)
    conv2 = mem.get_or_create("agent", "lead", 1)
    assert conv1.conversation_id == conv2.conversation_id


def test_get_or_create_new():
    mem = ConversationMemory()
    conv1 = mem.get_or_create("agent", "lead", 1)
    conv2 = mem.get_or_create("agent", "lead", 2)
    assert conv1.conversation_id != conv2.conversation_id


def test_list_conversations():
    mem = ConversationMemory()
    mem.create("a", "lead")
    mem.create("b", "ticket")
    mem.create("a", "ticket")

    all_convs = mem.list_conversations()
    assert len(all_convs) == 3

    agent_a = mem.list_conversations(agent_name="a")
    assert len(agent_a) == 2


def test_stats():
    mem = ConversationMemory()
    c1 = mem.create("agent_a", "lead")
    c1.add_message("user", "hello")
    c1.add_message("assistant", "hi")
    c2 = mem.create("agent_b", "ticket")
    c2.add_message("user", "help")

    stats = mem.get_stats()
    assert stats["total_conversations"] == 2
    assert stats["total_messages"] == 3
    assert stats["by_agent"]["agent_a"] == 1


def test_duration_minutes():
    conv = Conversation(conversation_id="test", agent_name="test", context_type="test")
    assert conv.duration_minutes == 0
    conv.add_message("user", "start")
    conv.add_message("assistant", "end")
    assert conv.duration_minutes >= 0


def test_system_prompt_on_create():
    mem = ConversationMemory()
    conv = mem.create("agent", "lead", system_prompt="You are helpful")
    assert conv.message_count == 1
    assert conv.messages[0].role == "system"
    assert "helpful" in conv.messages[0].content
