from __future__ import annotations

from czm_cli.telegram.state import ConversationStore


def test_state_set_get_clear_and_ttl():
    now = [100.0]
    store = ConversationStore(ttl_seconds=10, clock=lambda: now[0])
    store.set(1, 2, "flow", {"x": 1})
    assert store.get(1, 2).name == "flow"
    assert store.get(1, 3) is None
    now[0] = 111.0
    assert store.get(1, 2) is None
    store.set(1, 2, "flow")
    now[0] = 122.0
    state, expired = store.get_with_expiry(1, 2)
    assert state is None
    assert expired is True
    store.set(1, 2, "flow")
    store.clear(1, 2)
    assert store.get(1, 2) is None
