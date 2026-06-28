from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from src.core.model.Table import Column
from src.utils.column_util import validator_column_decorator


class Data(BaseModel):
    name: str
    value: Any


class Document(BaseModel):
    id: str = str(uuid4())
    table_id: str
    table_name: str
    data: list[Data]


@validator_column_decorator
def make_doc_valid_data(column: Column, value: Any) -> Data:
    return Data(name=column.name, value=value)
