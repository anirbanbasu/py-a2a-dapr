from datetime import datetime
import logging
from abc import abstractmethod
from typing import Any, Dict
from dapr.actor import Actor, ActorInterface, actormethod


class TaskActorInterface(ActorInterface):
    @abstractmethod
    @actormethod(name="Echo")
    async def echo(self, data: Dict[str, Any] | None = None) -> str: ...

    @abstractmethod
    @actormethod(name="Cancel")
    async def cancel(self) -> str: ...


class TaskActor(Actor, TaskActorInterface):
    def __init__(self, ctx, actor_id):
        super().__init__(ctx, actor_id)
        self._cancelled = False
        self.logger = logging.getLogger(self.__class__.__name__)

    async def on_activate(self) -> None:
        self.logger.debug(f"{self.__class__.__name__} activated")

    async def on_deactivate(self) -> None:
        self.logger.debug(f"{self.__class__.__name__} deactivated")

    async def echo(self, data: Dict[str, Any] | None = None) -> str:
        if self._cancelled:
            return "Cancelled"
        if not data or "input_text" not in data:
            return "Hello World! No input text to echo was provided."
        else:
            return f"Echo from {TaskActor.__name__} ({self.id}): {data['input_text']} @ {datetime.now().isoformat()}"

    async def cancel(self) -> str:
        self._cancelled = True
        return "Cancel signal received"
