from functools import wraps
from typing import Any, Callable

from pydantic import BaseModel

from src.exceptions.AbelDBException import AbelDBException
from src.utils.column_util import (
    check_bool,
    check_date,
    check_datetime,
    check_decimal,
    check_dict,
    check_enum,
    check_float,
    check_int,
    check_list,
    check_set,
    check_str,
    check_text,
    check_tuple,
)
from src.utils.constants import COLUMN_NOT_MATCH, INVALID_TYPE, TYPE_NAME_NOT_FOUND
from src.utils.status_enum import StatusEnum


class DataCheck(BaseModel):
    name: str
    value: Any


def validator_column_decorator(function: Callable) -> Callable:
    @wraps(function)
    def decorator(column: dict[str, Any], value: dict | BaseModel) -> Callable:
        new_value = value if value is dict else value.model_dump() if value is BaseModel else None

        if not new_value:
            raise AbelDBException(
                INVALID_TYPE,
                code=StatusEnum.BAD_REQUEST,
                info=["value type", "invalid", "must be base model or dict"],
            )

        new_value = DataCheck.model_validate(new_value)

        if new_value.name != column["name"]:
            raise AbelDBException(
                COLUMN_NOT_MATCH,
                code=StatusEnum.BAD_REQUEST,
                info=[
                    "not match",
                    f"value column='{value.name}'",
                    f"column name='{column['name']}'",
                ],
            )

        if not column["params"]["type_name"]:
            raise AbelDBException(
                TYPE_NAME_NOT_FOUND,
                code=StatusEnum.BAD_REQUEST,
                info=["column", "type_name", "not found"],
            )

        validator = {
            "bool": check_bool,
            "datetime.date": check_date,
            "datetime.datetime": check_datetime,
            "decimal.Decimal": check_decimal,
            "dict": check_dict,
            "enum": check_enum,
            "float": check_float,
            "int": check_int,
            "list": check_list,
            "set": check_set,
            "str": check_str,
            "text": check_text,
            "tuple": check_tuple,
        }.get(column["params"]["type_name"].value, None)

        if not validator:
            raise AbelDBException(
                INVALID_TYPE,
                code=StatusEnum.INTERNAL_ERROR,
                info=["field type", "invalid", column["params"]["type_name"].value],
            )

        result_validator = validator(new_value.value, column["params"])

        if result_validator != "success":
            raise AbelDBException(
                result_validator,
                code=StatusEnum.INTERNAL_ERROR,
                info=["column", "validation invalid"],
            )

        return function(column, new_value.value)

    return decorator
