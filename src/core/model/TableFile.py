from pydantic import BaseModel


class TableFile(BaseModel):
    name: str
    file: str
