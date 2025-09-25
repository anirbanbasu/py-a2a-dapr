from datetime import datetime
from abc import ABC
from typing import List, Optional

from typing_extensions import Annotated
from pydantic import BaseModel


class TaskActorInput(BaseModel, ABC):
    thread_id: Annotated[
        str,
        "Unique identifier for the thread (or task). Not called task_id to avoid confusion with A2A equivalent.",
    ]


class EchoInput(TaskActorInput):
    input: Annotated[Optional[str], "Input string to be echoed back"]


class EchoResponse(BaseModel):
    input: Annotated[Optional[str], "Input string to be echoed back"]
    output: Annotated[str, "Output echoed string"]
    timestamp: Annotated[datetime, "Timestamp when the response was generated"]
    actor_id: Annotated[Optional[str], "ID of the actor that processed the request"]


class EchoResponseWithHistory(BaseModel):
    current: Annotated[EchoResponse, "Current echoed response"]
    past: Annotated[List[EchoResponse], "History of echoed responses"]
