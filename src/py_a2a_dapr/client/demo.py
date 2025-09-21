import asyncio
import json
from dapr.actor import ActorProxy, ActorId, ActorProxyFactory
from dapr.clients.retry import RetryPolicy

from py_a2a_dapr.actor.hello_world import HelloWorldActorInterface


async def client_main():
    # Create proxy client
    factory = ActorProxyFactory(retry_policy=RetryPolicy(max_attempts=3))
    proxy = ActorProxy.create(
        "HelloWorldActor", ActorId("1"), HelloWorldActorInterface, factory
    )

    payload = {"input_text": "Hello from the client"}

    print(
        f"Response: {(await proxy.invoke_method('SayHello', json.dumps(payload).encode())).decode()}"
    )


def main():
    asyncio.run(client_main())


if __name__ == "__main__":
    main()
