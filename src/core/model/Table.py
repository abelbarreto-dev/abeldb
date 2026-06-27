from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from src.utils.column_util import validator_column_decorator
from src.utils.types_enum import TypesEnum

load_dotenv()


class ColumnParams(BaseModel):
    min_length: int = 0
    max_length: int = 255
    type_name: TypesEnum
    regex: str | None = None
    can_negative: bool = True
    is_nullable: bool = False
    is_unique: bool = False
    is_primary_key: bool = False
    is_foreign_key: bool = False
    fK_foreign_table_name: str | None = None
    fk_foreign_column_name: str | None = None
    fk_foreign_column_value: str | int | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Column(BaseModel):
    name: str
    params: ColumnParams
    document: list[Document]


class Table(BaseModel):
    id: str = uuid4()
    name: str
    database_id: str
    table_body: list[Column]


class DocData(BaseModel):
    column_name: str
    value: Any


class Document(BaseModel):
    doc_index: str
    data: list[DocData]


@validator_column_decorator
def make_doc_valid_data(value: Any, column: Column) -> Any:
    return DocData(column_name=column.name, value=value)
