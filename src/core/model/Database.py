from uuid import uuid4

from pydantic import BaseModel


class Database(BaseModel):
    id: str = str(uuid4())
    userId: str
    database: str
    tables_id: list[str] = []
