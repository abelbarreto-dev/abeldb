from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


class ColumnParams(BaseModel):
    min_length: int = 0
    max_length: int = 255
    value: str | int | float | bool | list | tuple | dict | date | datetime | Decimal | Enum
    regex: str | None = None
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


class Table(BaseModel):
    id: str = uuid4()
    name: str
    database_id: str
    table_body: list[Column]
