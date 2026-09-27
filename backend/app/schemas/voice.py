from pydantic import BaseModel


class VoiceTranscribeResponse(BaseModel):
    text: str
