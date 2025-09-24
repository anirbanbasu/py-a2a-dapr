import logging
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

from py_a2a_dapr.model.task import EchoInput, EchoResponseWithHistory

logger = logging.getLogger(__name__)


class GradioApp:
    def __init__(self):
        # self.ui = None
        self._a2a_uvicorn_host = env.str("APP_A2A_SRV_HOST", "127.0.0.1")
        self._a2a_uvicorn_port = env.int("APP_ECHO_A2A_SRV_PORT", 32769)
        self._a2a_base_url = f"http://{self._a2a_uvicorn_host}:{self._a2a_uvicorn_port}"

    def component_single_a2a_actor(self, bstate_ids):
        with gr.Column() as component:
            with gr.Accordion(label="Agent info", open=False):
                json_agent_card = gr.JSON(label="A2A Agent Card")
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    with gr.Row(equal_height=True):
                        btn_chat_delete = gr.Button(
                            "Delete chat", size="sm", variant="stop"
                        )
                        btn_new_chat = gr.Button("New chat", size="sm")
                    list_task_ids = gr.List(
                        wrap=True, headers=["Existing chats"], interactive=False
                    )
                    selected_chat_id = gr.State(value=None)
                with gr.Column(scale=3):
                    bstate_chat_histories = gr.BrowserState(
                        storage_key="a2a_dapr_chat_histories",
                        secret="a2a_dapr_bstate_secret",
                    )
                    chatbot = gr.Chatbot(
                        type="messages",
                        label="Chat History",
                    )
                    with gr.Row(equal_height=True):
                        txt_input = gr.Textbox(
                            lines=1, scale=3, placeholder="Type a message..."
                        )
                        btn_echo = gr.Button("Send", scale=1)
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

            @gr.on(
                triggers=[bstate_ids.change, self.ui.load],
                inputs=[bstate_ids],
                outputs=[list_task_ids],
            )
            async def btn_chats_refresh_clicked(browser_state_ids):
                if browser_state_ids:
                    yield (
                        [browser_state_ids]
                        if isinstance(browser_state_ids, str)
                        else browser_state_ids
                    )
                else:
                    yield []

            @gr.on(
                triggers=[list_task_ids.select],
                inputs=[bstate_chat_histories],
                outputs=[selected_chat_id, chatbot],
            )
            async def list_task_ids_selected(evt: gr.SelectData, chat_histories: dict):
                yield (
                    evt.value,
                    gr.update(
                        value=chat_histories.get(evt.value, []),
                        label=f"Chat ID: {evt.value}",
                    ),
                )

            @gr.on(
                triggers=[btn_chat_delete.click],
                inputs=[bstate_ids, bstate_chat_histories, selected_chat_id],
                outputs=[bstate_ids, bstate_chat_histories, selected_chat_id],
            )
            async def btn_chat_delete_clicked(
                browser_state_ids, browser_state_chat_histories: dict, selected_chat_id
            ):
                if (
                    selected_chat_id
                    and browser_state_ids
                    and browser_state_chat_histories
                ):
                    if isinstance(browser_state_ids, list):
                        if selected_chat_id in browser_state_ids:
                            browser_state_ids.remove(selected_chat_id)
                    elif isinstance(browser_state_ids, str):
                        if selected_chat_id == browser_state_ids:
                            browser_state_ids = []
                    if selected_chat_id in browser_state_chat_histories:
                        del browser_state_chat_histories[selected_chat_id]
                    selected_chat_id = None
                yield browser_state_ids, browser_state_chat_histories, selected_chat_id

            @gr.on(
                triggers=[btn_new_chat.click],
                inputs=[bstate_ids],
                outputs=[bstate_ids],
            )
            async def btn_new_chat_clicked(browser_state_ids):
                new_chat_id = str(uuid4())
                if browser_state_ids:
                    if isinstance(browser_state_ids, list):
                        browser_state_ids.append(new_chat_id)
                    else:
                        browser_state_ids = [browser_state_ids, new_chat_id]
                else:
                    browser_state_ids = [new_chat_id]

                yield gr.update(value=browser_state_ids)

            @gr.on(
                triggers=[btn_echo.click, txt_input.submit],
                inputs=[
                    txt_input,
                    selected_chat_id,
                    bstate_chat_histories,
                    chatbot,
                    bstate_ids,
                ],
                outputs=[
                    txt_input,
                    bstate_chat_histories,
                    chatbot,
                    json_agent_card,
                    bstate_ids,
                ],
            )
            async def btn_echo_clicked(
                txt_input: str,
                selected_chat: str,
                browser_state_chat_histories: dict,
                chat_history: list,
                browser_state_ids,
            ):
                selected_chat_id = selected_chat if selected_chat else str(uuid4())
                if isinstance(browser_state_ids, list):
                    if selected_chat_id not in browser_state_ids:
                        browser_state_ids.append(selected_chat_id)
                else:
                    browser_state_ids = [selected_chat_id]
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

                    yield (
                        None,
                        browser_state_chat_histories,
                        None,
                        final_agent_card_to_use.model_dump(),
                        gr.update(value=browser_state_ids),
                    )

                    client = ClientFactory(
                        config=ClientConfig(
                            streaming=True, polling=True, httpx_client=httpx_client
                        )
                    ).create(card=final_agent_card_to_use)
                    logger.info("A2A client initialised.")

                    input_data = EchoInput(
                        task_id=selected_chat_id,
                        input=txt_input,
                    )

                    send_message = Message(
                        role="user",
                        parts=[{"kind": "text", "text": input_data.model_dump_json()}],
                        messageId=uuid4().hex,
                    )

                    streaming_response = client.send_message(send_message)
                    async for response in streaming_response:
                        if isinstance(response, Message):
                            response_with_history = (
                                EchoResponseWithHistory.model_validate_json(
                                    response.parts[0].root.text
                                )
                            )
                            if len(chat_history) == 0:
                                # Add any historical messages first -- they are already in reverse chronological order
                                for past_message in response_with_history.past:
                                    chat_history.append(
                                        gr.ChatMessage(
                                            role="user",
                                            content=past_message.input,
                                        )
                                    )
                                    msg_id = str(uuid4())
                                    chat_history.append(
                                        gr.ChatMessage(
                                            role="assistant",
                                            content="",
                                            metadata={
                                                "title": f"Dapr Actor {past_message.actor_id}",
                                                "log": past_message.timestamp.isoformat(),
                                                "status": "done",
                                                "parent_id": msg_id,
                                            },
                                        )
                                    )
                                    chat_history.append(
                                        gr.ChatMessage(
                                            role="assistant",
                                            content=past_message.output,
                                            metadata={
                                                "id": msg_id,
                                            },
                                        )
                                    )
                            chat_history.append(
                                gr.ChatMessage(
                                    role="user",
                                    content=response_with_history.current.input,
                                )
                            )
                            msg_id = str(uuid4())
                            chat_history.append(
                                gr.ChatMessage(
                                    role="assistant",
                                    content="",
                                    metadata={
                                        "title": f"Dapr Actor {response_with_history.current.actor_id}",
                                        "log": response_with_history.current.timestamp.isoformat(),
                                        "status": "done",
                                        "parent_id": msg_id,
                                    },
                                )
                            )
                            chat_history.append(
                                gr.ChatMessage(
                                    role="assistant",
                                    content=response_with_history.current.output,
                                )
                            )
                            browser_state_chat_histories[selected_chat_id] = (
                                chat_history
                            )
                            yield (
                                None,
                                browser_state_chat_histories,
                                gr.update(
                                    value=chat_history,
                                    label=f"Chat ID: {selected_chat_id}",
                                ),
                                final_agent_card_to_use.model_dump(),
                                gr.update(value=browser_state_ids),
                            )
                        else:
                            logger.info(f"Received non-Message response: {response}")
                            ic(response, type(response))

            return component

    def construct_ui(self):
        with gr.Blocks(fill_width=True, fill_height=True) as self.ui:
            gr.Markdown("# A2A Dapr Gradio Interface")

            bstate_ids = gr.BrowserState(
                storage_key="a2a_dapr_bstate_ids", secret="a2a_dapr_bstate_secret"
            )

            with gr.Tab(label="Single A2A endpoint, single actor"):
                self.component_single_a2a_actor(bstate_ids)

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
