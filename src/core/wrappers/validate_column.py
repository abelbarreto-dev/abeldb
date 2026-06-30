from functools import wraps
from typing import Any, Callable

from src.exceptions.AbelDBException import AbelDBException
from src.utils.constants import (
    FOREIGN_KEY_SETTINGS_INVALID,
    PRIMARY_FOREIGN_KEY,
    STRING_INVALID_LENGTH,
    TEXT_INVALID_LENGTH,
)
from src.utils.status_enum import StatusEnum
from src.utils.types_enum import TypesEnum


def validator_column(function: Callable) -> Callable:
    @wraps(function)
    def decorator(column: dict[str, Any]) -> Callable:
        if (
            column["params"]["type_name"].value == TypesEnum.STR.value
            and column["params"]["min_length"] < 0
            and column["params"]["min_length"] > column["params"]["max_length"]
        ):
            raise AbelDBException(
                STRING_INVALID_LENGTH,
                code=StatusEnum.FORBIDDEN,
                info=[
                    "column.params",
                    "type_name",
                    "string",
                    "min_length",
                    "max_length",
                    "negative",
                    "min_length > max_length",
                ],
            )

        if (
            column["params"]["type_name"].value == TypesEnum.TEXT.value
            and column["params"]["min_length"] < 0
        ):
            raise AbelDBException(
                TEXT_INVALID_LENGTH,
                code=StatusEnum.FORBIDDEN,
                info=["column.params", "type_name", "text", "min_length", "negative"],
            )

        if column["params"]["is_primary_key"] and column["params"]["is_foreign_key"]:
            raise AbelDBException(
                PRIMARY_FOREIGN_KEY,
                code=StatusEnum.FORBIDDEN,
                info=["colum.params", "is_primary_key", "is_foreign_key"],
            )

        if column["params"]["is_foreign_key"] and (
            not column["params"]["fK_foreign_table_name"]
            or not column["params"]["fk_foreign_column_name"]
            or not column["params"]["fk_relation_type"]
        ):
            raise AbelDBException(
                FOREIGN_KEY_SETTINGS_INVALID,
                code=StatusEnum.FORBIDDEN,
                info=[
                    "column.params",
                    "is_foreign_key",
                    "fK_foreign_table_name",
                    "fk_foreign_column_name",
                    "fk_foreign_column_value",
                ],
            )

        return function(column)

    return decorator
