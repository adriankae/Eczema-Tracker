from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Callable


EXPIRED_STATE_MESSAGE = "That flow expired. Tap /menu to start again."


@dataclass(slots=True)
class ConversationState:
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0


class ConversationStore:
    def __init__(self, *, ttl_seconds: int = 900, clock: Callable[[], float] = monotonic):
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._states: dict[tuple[int, int], ConversationState] = {}

    def set(self, chat_id: int, user_id: int, name: str, data: dict[str, Any] | None = None) -> ConversationState:
        state = ConversationState(name=name, data=data or {}, created_at=self.clock())
        self._states[(chat_id, user_id)] = state
        return state

    def get(self, chat_id: int, user_id: int) -> ConversationState | None:
        state, _expired = self.get_with_expiry(chat_id, user_id)
        return state

    def get_with_expiry(self, chat_id: int, user_id: int) -> tuple[ConversationState | None, bool]:
        key = (chat_id, user_id)
        state = self._states.get(key)
        if state is None:
            return None, False
        if self.clock() - state.created_at > self.ttl_seconds:
            self.clear(chat_id, user_id)
            return None, True
        return state, False

    def clear(self, chat_id: int, user_id: int) -> None:
        self._states.pop((chat_id, user_id), None)
