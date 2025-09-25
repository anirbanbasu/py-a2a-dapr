from dapr.clients import DaprClient
from dapr.actor import ActorProxy, ActorId, ActorProxyFactory
from dapr.clients.retry import RetryPolicy
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from py_a2a_dapr.actor.task import TaskActorInterface
from py_a2a_dapr.model.task import EchoInput


class EchoAgentExecutor(AgentExecutor):
    def __init__(self):
        self._actor_type = "TaskActor"
        self._factory = ActorProxyFactory(retry_policy=RetryPolicy(max_attempts=3))
        self._dapr_client = DaprClient()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        input_data = EchoInput.model_validate_json(context.get_user_input())
        if not input_data or input_data.thread_id.strip() == "":
            raise ValueError(("Missing mandatory thread_id in the input!"))

        proxy = ActorProxy.create(
            actor_type=self._actor_type,
            actor_id=ActorId(actor_id=input_data.thread_id),
            actor_interface=TaskActorInterface,
            actor_proxy_factory=self._factory,
        )

        result = await proxy.invoke_method(
            method="Echo", raw_body=input_data.model_dump_json().encode()
        )
        await event_queue.enqueue_event(
            new_agent_text_message(text=result.decode().strip("\"'"))
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        input_data = EchoInput.model_validate_json(
            context._params.message.parts[0].root.text
        )
        if not input_data or input_data.thread_id.strip() == "":
            raise ValueError(("Missing mandatory thread_id in the input!"))

        proxy = ActorProxy.create(
            actor_type=self._actor_type,
            actor_id=ActorId(actor_id=input_data.thread_id),
            actor_interface=TaskActorInterface,
            actor_proxy_factory=self._factory,
        )
        result = await proxy.invoke_method(method="Cancel")
        await event_queue.enqueue_event(
            new_agent_text_message(text=result.decode().strip("\"'"))
        )
