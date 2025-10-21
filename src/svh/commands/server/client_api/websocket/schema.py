from pydantic import BaseModel, Field
from typing import Any, Literal, Optional

# Client -> Server


class ClientHello(BaseModel):
    type: Literal["hello"] = "hello"
    client: Optional[str] = None


class ClientDevPopup(BaseModel):
    type: Literal["dev_popup"] = "dev_popup"
    text: str = Field(default="")


ClientMessage = ClientHello | ClientDevPopup  # Pydantic v2 union


# Server -> Client
class ServerMessage(BaseModel):
    type: Literal["popup"] = "popup"
    text: str


class Echo(BaseModel):
    type: Literal["echo"] = "echo"
    payload: Any
