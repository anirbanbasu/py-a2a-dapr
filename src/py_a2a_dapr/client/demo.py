import asyncio
import json
from uuid import uuid4
from dapr.actor import ActorProxy, ActorId, ActorProxyFactory
from dapr.clients.retry import RetryPolicy

from py_a2a_dapr.actor.hello_world import EchoActorInterface


async def client_main():
    # Create proxy client
    factory = ActorProxyFactory(retry_policy=RetryPolicy(max_attempts=3))
    proxy = ActorProxy.create(
        "EchoActor", ActorId(str(uuid4())), EchoActorInterface, factory
    )

    payload = {"input_text": "Hello from the client"}

    print(
        f"Response: {(await proxy.invoke_method('Echo', json.dumps(payload).encode())).decode()}"
    )


def main():
    asyncio.run(client_main())


if __name__ == "__main__":
    main()
