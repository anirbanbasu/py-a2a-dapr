import logging
from typing import Any
from uuid import uuid4


from a2a.client import A2ACardResolver, ClientFactory, ClientConfig
from a2a.types import (
    Message,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
)

import httpx
from py_a2a_dapr import env, ic
import gradio as gr

from py_a2a_dapr.model.task import EchoInput

logger = logging.getLogger(__name__)


class GradioApp:
    def __init__(self):
        self.ui = None
        self._a2a_uvicorn_host = env.str("APP_A2A_SRV_HOST", "127.0.0.1")
        self._a2a_uvicorn_port = env.int("APP_ECHO_A2A_SRV_PORT", 32769)
        self._a2a_base_url = f"http://{self._a2a_uvicorn_host}:{self._a2a_uvicorn_port}"

    def component_single_a2a_actor(self, bstate_id):
        with gr.Column() as component:
            with gr.Row(equal_height=True):
                txt_input = gr.Textbox(
                    label="Input", lines=4, placeholder="Type something..."
                )
                with gr.Column():
                    gr.Examples(
                        label="Example of input messages",
                        examples=[
                            "Ahoy there, matey!",
                            "Hello there!",
                            "Test",
                            "Echo this?",
                        ],
                        inputs=[txt_input],
                    )
                    with gr.Row(equal_height=True):
                        btn_echo = gr.Button("Echo")
                        gr.Button("Show message history")
            with gr.Row(equal_height=True):
                json_agent_card = gr.JSON(label="A2A Agent Card")
                json_output = gr.JSON(label="Output")

            @gr.on(
                triggers=[btn_echo.click],
                inputs=[txt_input, bstate_id],
                outputs=[json_output, json_agent_card, bstate_id],
            )
            async def btn_echo_clicked(txt_input: str, browser_state_id):
                if not browser_state_id:
                    browser_state_id = str(uuid4())
                async with httpx.AsyncClient(timeout=600) as httpx_client:
                    resolver = A2ACardResolver(
                        httpx_client=httpx_client,
                        base_url=self._a2a_base_url,
                    )
                    # Fetch Public Agent Card and Initialize Client
                    logger.info(
                        f"Attempting to fetch public agent card from: {self._a2a_base_url}{AGENT_CARD_WELL_KNOWN_PATH}"
                    )
                    final_agent_card_to_use = await resolver.get_agent_card()
                    logger.info("Successfully fetched public agent card:")

                    yield (
                        None,
                        final_agent_card_to_use.model_dump(),
                        gr.update(value=browser_state_id),
                    )

                    client = ClientFactory(
                        config=ClientConfig(
                            streaming=True, polling=True, httpx_client=httpx_client
                        )
                    ).create(card=final_agent_card_to_use)
                    logger.info("A2A Client initialised.")

                    input_data = EchoInput(
                        task_id=browser_state_id,
                        input=txt_input,
                    )

                    send_message: dict[str, Any] = {
                        "role": "user",
                        "parts": [
                            {"kind": "text", "text": input_data.model_dump_json()}
                        ],
                        "messageId": uuid4().hex,
                    }

                    streaming_response = client.send_message(Message(**send_message))
                    async for response in streaming_response:
                        if isinstance(response, Message):
                            # print(response.model_dump(mode="json", exclude_none=True))
                            yield (
                                response.parts[0].root.text,
                                final_agent_card_to_use.model_dump(),
                                gr.update(value=browser_state_id),
                            )
                        else:
                            logger.info(f"Received non-Message response: {response}")
                            ic(response, type(response))

            return component

    def construct_ui(self):
        with gr.Blocks(fill_width=True, fill_height=True) as self.ui:
            gr.Markdown("# A2A Dapr Gradio Interface")

            bstate_id = gr.BrowserState(
                storage_key="a2a_dapr_bstate_id", secret="a2a_dapr_bstate_secret"
            )

            with gr.Tab(label="Single A2A endpoint, single actor"):
                self.component_single_a2a_actor(bstate_id)

        return self.ui

    def shutdown(self):
        if self.ui and self.ui.is_running:
            self.ui.close()


def main():
    app = GradioApp()

    try:
        app.construct_ui().queue().launch(share=False, ssr_mode=False, show_api=False)
    except InterruptedError:
        logger.warning("Gradio server interrupted, shutting down...")
    except Exception as e:
        logger.error(f"Error starting Gradio server. {e}")
    finally:
        if app:
            app.shutdown()


if __name__ == "__main__":
    main()
