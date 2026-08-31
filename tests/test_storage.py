import json

import pytest

from aui import AppStorage, JSONStore, MemoryStore, SceneStorage


def test_memory_store_behaves_like_a_mapping():
    store = MemoryStore({"theme": "system"})
    store["theme"] = "dark"
    store["count"] = 2

    assert dict(store) == {"theme": "dark", "count": 2}
    del store["count"]
    assert len(store) == 1


def test_app_storage_shares_store_and_binding_updates_it():
    store = MemoryStore()
    first = AppStorage("name", "Guest", store=store)
    second = AppStorage("name", "Other", store=store)

    assert first.value == second.value == "Guest"
    first.binding().value = "Taylor"
    assert store["name"] == "Taylor"

    refreshed = AppStorage("name", "Ignored", store=store)
    assert refreshed.value == "Taylor"


def test_scene_storage_is_shared_per_scene_and_isolated_between_scenes():
    scene_a = "test-storage-scene-a"
    scene_b = "test-storage-scene-b"
    first = SceneStorage("draft", "", scene_id=scene_a)
    first.value = "hello"

    assert SceneStorage("draft", "ignored", scene_id=scene_a).value == "hello"
    assert SceneStorage("draft", "separate", scene_id=scene_b).value == "separate"


def test_json_store_round_trip(tmp_path):
    path = tmp_path / "preferences" / "settings.json"
    store = JSONStore(path)
    store["theme"] = "dark"
    store["zoom"] = 1.25

    assert JSONStore(path)["theme"] == "dark"
    assert json.loads(path.read_text(encoding="utf-8"))["zoom"] == 1.25


def test_json_store_rejects_non_object_root(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be an object"):
        JSONStore(path)


def test_json_store_rolls_back_non_serializable_value(tmp_path):
    store = JSONStore(tmp_path / "settings.json")
    store["valid"] = True

    with pytest.raises(TypeError):
        store["invalid"] = object()

    assert dict(store) == {"valid": True}
    assert dict(JSONStore(store.path)) == {"valid": True}


def test_json_store_rolls_back_failed_delete(tmp_path, monkeypatch):
    store = JSONStore(tmp_path / "settings.json")
    store["theme"] = "dark"
    monkeypatch.setattr(store, "_write", lambda: (_ for _ in ()).throw(OSError("disk")))

    with pytest.raises(OSError, match="disk"):
        del store["theme"]

    assert store["theme"] == "dark"


def test_app_storage_requires_a_key():
    with pytest.raises(ValueError, match="cannot be empty"):
        AppStorage("", False)
