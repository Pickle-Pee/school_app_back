from pydantic import BaseModel


class ClassGroupOut(BaseModel):
    id: int
    grade: int
    letter: str
    name: str

    class Config:
        orm_mode = True
