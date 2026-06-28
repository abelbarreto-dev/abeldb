from decimal import Decimal
from re import compile
from typing import Any

from src.utils.types_enum import TypesEnum


def get_column_type_value_str(value: Any) -> str:
    type_name = str(type(value))
    type_name = (
        type_name.replace("<", "").replace(">", "").replace("class ", "").replace("'", "")
    ).split(" ")[0]
    return type_name


def check_bool(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.BOOL.value:
        return "value does not match type boolean"

    return "success"


def check_date(value, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.DATE.value:
        return "value does not match type date"

    return "success"


def check_datetime(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.DATETIME.value:
        return "value does not match type datetime"

    return "success"


def check_decimal(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.DECIMAL.value:
        return "value does not match type decimal"

    test_value = Decimal(value) if isinstance(value, Decimal) else Decimal(-1)

    if not params["can_negative"] and test_value < 0:
        return "value cannot be negative"

    return "success"


def check_dict(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.DICT.value:
        return "value does not match type dictionary"

    return "success"


def check_enum(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.ENUM.value:
        return "value does not match type enum"

    return "success"


def check_float(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.FLOAT.value:
        return "value does not match type float"

    test_value = int(value) if isinstance(value, float) else -1

    if not params["can_negative"] and test_value < 0:
        return "value cannot be negative"

    return "success"


def check_int(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.INT.value:
        return "value does not match type int"

    test_value = int(value) if isinstance(value, int) else -1

    if not params["can_negative"] and test_value < 0:
        return "value cannot be negative"

    return "success"


def check_list(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.LIST.value:
        return "value does not match type list"

    return "success"


def check_set(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.SET.value:
        return "value does not match type set"

    return "success"


def check_str(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.STR.value:
        return "value does not match type string"

    test_value = str(value) if isinstance(value, str) else "a/+*_fail_*+\\"

    if params["regex"]:
        compiled_regex = compile(params["regex"])

        result = compiled_regex.match(test_value) is not None
        if not result:
            return "value does not match regex"

    if params["min_length"] < 0:
        return "min length cannot be negative"

    if params["min_length"] > params["max_length"]:
        return "min length cannot be greater than max length"

    if len(test_value) > params["max_length"]:
        return "value too long"
    elif len(test_value) < params["min_length"]:
        return "value too short"
    return "success"


def check_text(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    if params["min_length"] < 0:
        return "min length cannot be negative"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.STR.value:
        return "value does not match type text"

    if params["regex"]:
        compiled_regex = compile(params["regex"])

        test_value = str(value) if isinstance(value, str) else "a/+*_fail_*+\\"

        result = compiled_regex.match(test_value) is not None
        if not result:
            return "value does not match regex"

    return "success"


def check_tuple(value: Any, params: dict[str, Any]) -> str:
    if value is None and not params["is_nullable"]:
        return "value cannot be null"

    type_name = get_column_type_value_str(value)

    if not type_name == TypesEnum.TUPLE.value:
        return "value does not match type tuple"

    return "success"
