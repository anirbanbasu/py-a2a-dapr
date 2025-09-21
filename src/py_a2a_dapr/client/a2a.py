import logging

from typing import Any
from uuid import uuid4

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


async def a2a_client_connect() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    # --8<-- [start:A2ACardResolver]

    _a2a_uvicorn_host = env.str("APP_A2A_SRV_HOST", "127.0.0.1")
    _a2a_uvicorn_port = env.int("APP_A2A_SRV_PORT", 16800)
    base_url = f"http://{_a2a_uvicorn_host}:{_a2a_uvicorn_port}"

    async with httpx.AsyncClient(timeout=600) as httpx_client:
        # initialise A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )
        # --8<-- [end:A2ACardResolver]

        # Fetch Public Agent Card and initialise Client
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

        send_message_payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "Hello there, from an A2A client!"}],
                "messageId": uuid4().hex,
                "metadata": {"task_id": "t-1234-5678-90"},
            },
        }

        streaming_response = client.send_message(
            Message(**send_message_payload["message"])
        )
        async for response in streaming_response:
            if isinstance(response, Message):
                print(response.model_dump(mode="json", exclude_none=True))
        # --8<-- [end:send_message]


def main():
    import asyncio

    asyncio.run(a2a_client_connect())


if __name__ == "__main__":
    main()
