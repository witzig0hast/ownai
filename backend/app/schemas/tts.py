from pydantic import BaseModel


class TTSVoicesOut(BaseModel):
    voices: list[str]


class TTSSpeakIn(BaseModel):
    text: str
    voice: str | None = None
