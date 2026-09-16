"""
Unit tests for Sam Phase 5 Tiered Memory System.
"""
import pytest

from sam_memory.models import MemoryEntry
from sam_memory.semantic import SemanticMemoryEngine
from sam_memory.skill import MemorySkill
from sam_memory.store import SQLiteMemoryStore


@pytest.mark.asyncio
async def test_sqlite_memory_store_crud():
    store = SQLiteMemoryStore(db_path=":memory:")

    entry = MemoryEntry(
        category="preference",
        key="editor",
        value="VS Code",
        importance=4,
        tags=["dev", "tools"],
    )

    # 1. Add
    saved = await store.add_memory(entry)
    assert saved.id == entry.id

    # 2. Get by ID and Key
    retrieved = await store.get_by_id(saved.id)
    assert retrieved is not None
    assert retrieved.key == "editor"
    assert retrieved.value == "VS Code"

    by_key = await store.get_by_key("editor")
    assert by_key is not None
    assert by_key.value == "VS Code"

    # 3. Search
    results = await store.search_memories("VS Code")
    assert len(results) >= 1
    assert results[0].entry.key == "editor"

    # 4. List
    all_items = await store.list_memories()
    assert len(all_items) == 1

    # 5. Delete
    deleted = await store.delete_memory(saved.id)
    assert deleted
    assert await store.get_by_id(saved.id) is None


@pytest.mark.asyncio
async def test_sqlite_memory_store_forget():
    store = SQLiteMemoryStore(db_path=":memory:")
    await store.add_memory(MemoryEntry(key="secret_project_alpha", value="Confidential specs", category="project"))
    await store.add_memory(MemoryEntry(key="secret_project_beta", value="Next-gen assistant", category="project"))

    assert len(await store.list_memories()) == 2

    # Forget project alpha
    count = await store.forget("project_alpha")
    assert count == 1
    assert len(await store.list_memories()) == 1


def test_semantic_memory_engine():
    engine = SemanticMemoryEngine()
    entries = [
        MemoryEntry(key="favorite_food", value="I love home-made biryani", importance=3),
        MemoryEntry(key="operating_system", value="Running Windows 11 Pro", importance=4),
        MemoryEntry(key="user_hobby", value="Playing chess and coding algorithms", importance=5),
    ]

    # Query for food/biryani
    ranked = engine.rank("biryani food", entries)
    assert len(ranked) >= 1
    assert ranked[0].entry.key == "favorite_food"

    # Query for operating system
    ranked_os = engine.rank("windows system", entries)
    assert len(ranked_os) >= 1
    assert ranked_os[0].entry.key == "operating_system"


@pytest.mark.asyncio
async def test_memory_skill_tools():
    store = SQLiteMemoryStore(db_path=":memory:")
    skill = MemorySkill(store=store)
    tools = {t.name: t for t in skill.get_tools()}

    assert "remember_fact" in tools
    assert "recall_facts" in tools
    assert "list_memories" in tools
    assert "forget_memory" in tools

    # 1. remember_fact
    rem_res = await skill.execute(
        "remember_fact",
        {"key": "pet_name", "value": "Bruno", "category": "profile", "importance": 5},
    )
    assert rem_res.success
    assert "Bruno" in rem_res.data["message"]

    # 2. recall_facts
    rec_res = await skill.execute("recall_facts", {"query": "pet Bruno"})
    assert rec_res.success
    assert rec_res.data["count"] >= 1
    assert rec_res.data["results"][0]["value"] == "Bruno"

    # 3. list_memories
    list_res = await skill.execute("list_memories", {})
    assert list_res.success
    assert list_res.data["count"] == 1

    # 4. forget_memory
    forget_res = await skill.execute("forget_memory", {"query": "pet_name"})
    assert forget_res.success
    assert forget_res.data["deleted_count"] == 1
