from functools import partial
import logging

from uuid import uuid4
from asyncer import syncify

from rich import print_json

import httpx

from py_a2a_dapr import env

from a2a.client import A2ACardResolver, ClientFactory, ClientConfig
from a2a.types import (
    AgentCard,
    Message,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
)

from py_a2a_dapr.model.task import EchoInput, EchoResponseWithHistory

import typer

cli_app = typer.Typer(
    name="a2a-client",
    help="An A2A client example for py-a2a-dapr",
    no_args_is_help=True,
    add_completion=False,
)


@cli_app.command()
def hello(
    name: str = typer.Argument(default="World", help="The name to greet."),
) -> None:
    """
    A simple hello world command. This is a placeholder to ensure that
    there are more than one actual commands in this CLI app.
    """
    print(f"Hello, {name}!")


@cli_app.command()
@partial(syncify, raise_sync_error=False)
async def single_a2a_actor(
    message: str = typer.Argument(
        default="Hello there, from an A2A client!",
        help="The message to send to the A2A endpoint.",
    ),
    task_id: str = typer.Option(
        default=str(uuid4()),
        help="A task ID to identify your conversation. If not specified, a random UUID will be used.",
    ),
) -> None:
    """
    An example of connecting to a single A2A endpoint backed by a single actor type.
    """
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    _a2a_uvicorn_host = env.str("APP_A2A_SRV_HOST", "127.0.0.1")
    _a2a_uvicorn_port = env.int("APP_ECHO_A2A_SRV_PORT", 32769)
    base_url = f"http://{_a2a_uvicorn_host}:{_a2a_uvicorn_port}"

    async with httpx.AsyncClient(timeout=600) as httpx_client:
        # initialise A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                f"Attempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}"
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info("Successfully fetched public agent card:")
            logger.info(_public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card_to_use = _public_card

        except Exception as e:
            logger.error(
                f"Critical error fetching public agent card. {e}", exc_info=True
            )

        client = ClientFactory(
            config=ClientConfig(streaming=True, polling=True, httpx_client=httpx_client)
        ).create(card=final_agent_card_to_use)
        logger.info("A2A client initialised.")

        input_data = EchoInput(
            task_id=task_id,
            input=message,
        )

        send_message = Message(
            role="user",
            parts=[{"kind": "text", "text": input_data.model_dump_json()}],
            messageId=str(uuid4()),
        )
        logger.info("Sending message to the A2A endpoint")
        streaming_response = client.send_message(send_message)
        logger.info("Parsing streaming response from the A2A endpoint")
        async for response in streaming_response:
            if isinstance(response, Message):
                validated_response = EchoResponseWithHistory.model_validate_json(
                    response.parts[0].root.text
                )
                validated_response.past = validated_response.past[
                    ::-1
                ]  # Reverse to chronological order to look right in the CLI
                print_json(validated_response.model_dump_json())


def main():  # pragma: no cover
    cli_app()


if __name__ == "__main__":  # pragma: no cover
    main()
