from pydantic import BaseModel, Field


class TopicEnsureRequest(BaseModel):
    class_id: int = Field(..., ge=1)
    subject: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    model_config = {
        "from_attributes": True
    }

class TopicOut(BaseModel):
    id: int
    title: str

    model_config = {
        "from_attributes": True
    }