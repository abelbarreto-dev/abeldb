from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from src.utils.column_util import validator_column_params_decorator
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


class Table(BaseModel):
    id: str = str(uuid4())
    name: str
    database: str
    table_body: list[Column]


@validator_column_params_decorator
def validate_column_params(column: Column) -> dict:
    return column
