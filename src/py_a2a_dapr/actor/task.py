from datetime import datetime
import logging
from abc import abstractmethod
from dapr.actor import Actor, ActorInterface, actormethod
from gradio import List
from py_a2a_dapr.model.task import EchoInput, EchoResponse, EchoResponseWithHistory


class TaskActorInterface(ActorInterface):
    @abstractmethod
    @actormethod(name="Echo")
    async def echo(self, data: dict | None = None) -> dict | None: ...

    @abstractmethod
    @actormethod(name="Cancel")
    async def cancel(self) -> str: ...


logger = logging.getLogger(__name__)


class TaskActor(Actor, TaskActorInterface):
    def __init__(self, ctx, actor_id):
        super().__init__(ctx, actor_id)
        self._cancelled = False
        self._history_key = "echo_history"
        self.echo_history: List[str] = []

    async def on_activate(self) -> None:
        logger.debug(f"{self.__class__.__name__} activated")

    async def on_deactivate(self) -> None:
        logger.debug(f"{self.__class__.__name__} deactivated")

    async def echo(self, data: dict | None = None) -> dict | None:
        if self._cancelled:
            return None
        logger.debug(f"Echo called on actor {self.id} with data: {data}")
        self.echo_history = await self._state_manager.get_or_add_state(
            self._history_key, []
        )
        timestamp = datetime.now()
        input_data = EchoInput.model_validate(data) if data else None
        if not input_data or input_data.input.strip() == "":
            echo = f"{TaskActor.__name__}: Hello World! No input text to echo was provided!"
        else:
            echo = f"{TaskActor.__name__}: {input_data.input}"

        current = EchoResponse(
            input=input_data.input if input_data else None,
            output=echo,
            timestamp=timestamp,
            actor_id=str(self.id),
        )
        response = EchoResponseWithHistory(
            current=current,
            past=[
                EchoResponse.model_validate_json(message)
                for message in self.echo_history
            ],
        )
        self.echo_history.append(current.model_dump_json())
        await self._state_manager.set_state(self._history_key, self.echo_history)
        await self._state_manager.save_state()
        return response.model_dump()

    async def cancel(self) -> str:
        logger.debug(f"Cancel signal received for actor {self.id}")
        self._cancelled = True
        return "Cancel signal received"
