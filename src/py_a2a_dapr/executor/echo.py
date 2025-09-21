import json
from dapr.clients import DaprClient
from dapr.actor import ActorProxy, ActorId, ActorProxyFactory
from dapr.clients.retry import RetryPolicy
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from py_a2a_dapr.actor.task import TaskActorInterface


class EchoAgentExecutor(AgentExecutor):
    def __init__(self):
        self._actor_type = "TaskActor"
        self._factory = ActorProxyFactory(retry_policy=RetryPolicy(max_attempts=3))
        self._dapr_client = DaprClient()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        task_id = context._params.message.metadata.get("task_id")
        if not task_id or task_id.strip() == "":
            await event_queue.enqueue_event(
                new_agent_text_message("Missing task_id in request metadata")
            )
            return

        input_text = (
            context._params.message.parts[0].root.text
            if context._params.message.parts
            else None
        )
        # Call into actor (blocking style: get full result)

        # ic(context.__dict__)
        # ic(event_queue.__dict__)
        proxy = ActorProxy.create(
            actor_type=self._actor_type,
            actor_id=ActorId(actor_id=task_id),
            actor_interface=TaskActorInterface,
            actor_proxy_factory=self._factory,
        )

        payload = {"input_text": input_text}
        result = await proxy.invoke_method(
            method="Echo", raw_body=json.dumps(payload).encode()
        )
        await event_queue.enqueue_event(
            new_agent_text_message(text=result.decode().strip("\"'"))
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        task_id = context._params.message.metadata.get("task_id")
        if not task_id or task_id.strip() == "":
            await event_queue.enqueue_event(
                new_agent_text_message("Missing task_id in request metadata")
            )
            return

        proxy = ActorProxy.create(
            actor_type=self._actor_type,
            actor_id=ActorId(actor_id=task_id),
            actor_interface=TaskActorInterface,
            actor_proxy_factory=self._factory,
        )
        result = await proxy.invoke_method(method="Cancel")
        await event_queue.enqueue_event(
            new_agent_text_message(text=result.decode().strip("\"'"))
        )
