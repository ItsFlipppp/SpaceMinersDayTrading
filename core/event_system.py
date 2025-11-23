"""
Lightweight event dispatcher for game/feed updates.
"""


class EventBus:
    def __init__(self):
        self._subscribers = []

    def subscribe(self, handler):
        if handler not in self._subscribers:
            self._subscribers.append(handler)

    def emit(self, message, color="#cccccc"):
        for handler in list(self._subscribers):
            handler(message, color)
