from pydantic import BaseModel
from typing import Literal, Union


# --- Client to Server messages ---

class HelloMessage(BaseModel):
    type: Literal["hello"]
    client: str


class DevPopupMessage(BaseModel):
    type: Literal["dev_popup"]
    text: str


# Union of possible client messages
ClientMessage = Union[HelloMessage, DevPopupMessage]


# --- Server to Client messages ---

class PopupMessage(BaseModel):
    type: Literal["popup"]
    text: str


class ErrorMessage(BaseModel):
    type: Literal["error"]
    detail: str


# Union of possible server messages
ServerMessage = Union[PopupMessage, ErrorMessage]
