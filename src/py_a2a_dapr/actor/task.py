from datetime import datetime
import logging
from abc import abstractmethod
from typing import Any, Dict
from dapr.actor import Actor, ActorInterface, actormethod
from py_a2a_dapr import ic


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
        message_history = await self._state_manager.get_or_add_state(
            "message_history", []
        )
        ic(message_history)
        timestamp = datetime.now().isoformat()
        if not data or "input_text" not in data:
            input_msg = ""
            response = f"Echo from {TaskActor.__name__} ({self.id}): Hello World! No input text to echo was provided! @ {timestamp}"
        else:
            input_msg = data["input_text"]
            response = (
                f"Echo from {TaskActor.__name__} ({self.id}): {input_msg} @ {timestamp}"
            )
        message_history.append(
            {"input": input_msg, "response": response, "timestamp": timestamp}
        )
        await self._state_manager.set_state("message_history", message_history)
        await self._state_manager.save_state()
        return response

    async def cancel(self) -> str:
        self._cancelled = True
        return "Cancel signal received"
