# server.py
import asyncio
import signal
import sys
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from py_a2a_dapr import env
from py_a2a_dapr.executor.echo import EchoAgentExecutor


async def uvicorn_serve():
    def sigint_handler(signal, frame):
        """
        Signal handler to shut down the server gracefully.
        """
        print("Attempting graceful shutdown, please wait...")
        # This is absolutely necessary to exit the program
        sys.exit(0)

    _a2a_uvicorn_host = env.str("APP_A2A_SRV_HOST", "127.0.0.1")
    _a2a_uvicorn_port = env.int("APP_A2A_SRV_PORT", 16800)
    signal.signal(signal.SIGINT, sigint_handler)

    skill = AgentSkill(
        id="echo_skill",
        name="Echo",
        description="Echo input messages",
        tags=["hello", "echo"],
        examples=["Ahoy, matey!", "Hello, world!", "Good morning!"],
    )
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name="Echo Agent",
        description="An agent that can echo input messages",
        url=f"http://{_a2a_uvicorn_host}:{_a2a_uvicorn_port}/",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        supports_authenticated_extended_card=False,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=EchoAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    a2a_app = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )
    config = uvicorn.Config(
        a2a_app.build(),
        host=_a2a_uvicorn_host,
        port=_a2a_uvicorn_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def main():
    """
    Main function to run the ACP server.
    """
    asyncio.run(uvicorn_serve())


if __name__ == "__main__":
    main()
