from pydantic import BaseModel


class VisionDescribeResponse(BaseModel):
    ocr_text: str | None
    description: str | None
