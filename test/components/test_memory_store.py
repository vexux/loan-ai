import pytest
from contracts.memory.memory_contract import MemoryRecord, MemoryRequest
from components.memory.in_memory_store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_memory_save_and_retrieve():
    store = InMemoryMemoryStore()
    
    await store.save(MemoryRecord(memory_id="1", session_id="sess_A", user_id="u1", content="Hello"))
    await store.save(MemoryRecord(memory_id="2", session_id="sess_A", user_id="u1", content="How can I help?"))
    await store.save(MemoryRecord(memory_id="3", session_id="sess_B", user_id="u2", content="Other session"))

    res_a = await store.retrieve(MemoryRequest(session_id="sess_A"))
    assert res_a.success is True
    assert len(res_a.data) == 2

    res_b = await store.retrieve(MemoryRequest(session_id="sess_B"))
    assert res_b.success is True
    assert len(res_b.data) == 1
    assert res_b.data[0].content == "Other session"


@pytest.mark.asyncio
async def test_dialogue_history_formatting():
    store = InMemoryMemoryStore()
    await store.save(MemoryRecord(memory_id="1", session_id="sess_1", user_id="u1", content="User Question", metadata={"speaker": "User"}))
    await store.save(MemoryRecord(memory_id="2", session_id="sess_1", user_id="u1", content="Agent Answer", metadata={"speaker": "Agent"}))

    history = await store.get_dialogue_history("sess_1", limit=2)
    assert "User: User Question" in history
    assert "Agent: Agent Answer" in history
