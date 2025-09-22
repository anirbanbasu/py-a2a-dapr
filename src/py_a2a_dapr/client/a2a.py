import logging

from typing import Any
from uuid import uuid4
import asyncio

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

from py_a2a_dapr.model.task import EchoInput


async def a2a_echo_client() -> None:
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
            logger.info(
                "\nUsing PUBLIC agent card for client initialization (default)."
            )

        except Exception as e:
            logger.error(
                f"Critical error fetching public agent card: {e}", exc_info=True
            )
            raise RuntimeError(
                "Failed to fetch the public agent card. Cannot continue."
            ) from e

        # --8<-- [start:send_message]
        client = ClientFactory(
            config=ClientConfig(streaming=True, polling=True, httpx_client=httpx_client)
        ).create(card=final_agent_card_to_use)
        logger.info("A2A Client initialised.")

        input_data = EchoInput(
            task_id="t-1234-5678-90",
            input="Hello there, from an A2A client!",
        )

        send_message: dict[str, Any] = {
            "role": "user",
            "parts": [{"kind": "text", "text": input_data.model_dump_json()}],
            "messageId": uuid4().hex,
        }

        streaming_response = client.send_message(Message(**send_message))
        async for response in streaming_response:
            if isinstance(response, Message):
                print(response.parts[0].root.text)
        # --8<-- [end:send_message]


def main():
    asyncio.run(a2a_echo_client())


if __name__ == "__main__":
    main()
