from pydantic import BaseModel, ConfigDict


class ClassGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade: int
    letter: str
    name: str

