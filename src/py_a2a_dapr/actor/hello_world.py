import asyncio
import logging
from abc import abstractmethod
from dapr.actor import Actor, ActorInterface, actormethod


class HelloWorldActorInterface(ActorInterface):
    @abstractmethod
    @actormethod(name="SayHello")
    async def say_hello(self, input_text: str | None = None) -> str: ...

    @abstractmethod
    @actormethod(name="Cancel")
    async def cancel(self) -> str: ...


class HelloWorldActor(Actor, HelloWorldActorInterface):
    def __init__(self, ctx, actor_id):
        super().__init__(ctx, actor_id)
        self._cancelled = False
        self.logger = logging.getLogger(self.__class__.__name__)

    async def on_activate(self) -> None:
        self.logger.warning(f"{self.__class__.__name__} activated")

    async def on_deactivate(self) -> None:
        self.logger.warning(f"{self.__class__.__name__} deactivated")

    async def say_hello(self, input_text: str | None = None) -> str:
        result = []
        for i in range(3):
            if self._cancelled:
                return "Cancelled"
            await asyncio.sleep(1)  # simulate work
            if input_text:
                result.append(f"Step {i}: processed {input_text}")
            else:
                result.append(f"Step {i}: no input provided")
        return "; ".join(result)

    async def cancel(self) -> str:
        self._cancelled = True
        return "Cancel signal received"
