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

logger = logging.getLogger(__name__)


class GradioApp:
    def __init__(self):
        self.ui = None
        self._a2a_uvicorn_host = env.str("APP_A2A_SRV_HOST", "127.0.0.1")
        self._a2a_uvicorn_port = env.int("APP_A2A_SRV_PORT", 16800)
        self._a2a_base_url = f"http://{self._a2a_uvicorn_host}:{self._a2a_uvicorn_port}"

    def construct_ui(self):
        with gr.Blocks() as self.ui:
            gr.Markdown("# A2A Dapr Gradio Interface")

            bstate_id = gr.BrowserState(
                storage_key="a2a_dapr_bstate_id", secret="a2a_dapr_bstate_secret"
            )

            with gr.Row(equal_height=True):
                txt_input = gr.Textbox(
                    label="Input", lines=4, placeholder="Type something..."
                )
                txt_output = gr.Textbox(
                    label="Output", lines=4, placeholder="Output will appear here..."
                )
            gr.Examples(
                examples=["Ahoy there, matey!", "Hello there!", "Test", "Echo this?"],
                inputs=[txt_input],
            )
            btn_submit = gr.Button("Submit")
            lbl_status = gr.Markdown("> Ready")

            @gr.on(
                triggers=[btn_submit.click],
                inputs=[txt_input, bstate_id],
                outputs=[txt_output, lbl_status, bstate_id],
            )
            async def btn_submit_clicked(txt_input: str, browser_state_id):
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
                    logger.info(
                        final_agent_card_to_use.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )

                    yield (
                        None,
                        "> Fetched public agent card from A2A server.",
                        gr.update(value=browser_state_id),
                    )

                    client = ClientFactory(
                        config=ClientConfig(
                            streaming=True, polling=True, httpx_client=httpx_client
                        )
                    ).create(card=final_agent_card_to_use)
                    logger.info("A2A Client initialised.")

                    send_message_payload: dict[str, Any] = {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": txt_input}],
                            "messageId": uuid4().hex,
                            "metadata": {"task_id": browser_state_id},
                        },
                    }

                    streaming_response = client.send_message(
                        Message(**send_message_payload["message"])
                    )
                    async for response in streaming_response:
                        if isinstance(response, Message):
                            # print(response.model_dump(mode="json", exclude_none=True))
                            yield (
                                response.parts[0].root.text,
                                "> Received response message.",
                                gr.update(value=browser_state_id),
                            )
                        else:
                            logger.info(f"Received non-Message response: {response}")
                            ic(response, type(response))

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
