from uuid import uuid4

from pydantic import BaseModel

from src.core.model.Relation import Relation
from src.core.model.TableFile import TableFile


class Database(BaseModel):
    id: str = str(uuid4())
    userId: str
    database: str
    table_files: list[TableFile] = []
    relations: list[Relation] = []
