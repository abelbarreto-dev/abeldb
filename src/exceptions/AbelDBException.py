import sys
from types import TracebackType
from typing import Any, Self

from typing_extensions import disjoint_base

from src.utils.status_enum import StatusEnum


@disjoint_base
class BaseError:
    name: str
    info: list[str]
    message: str
    code: str
    args: tuple[Any, ...]
    __cause__: BaseError | None
    __context__: BaseError | None
    __suppress_context__: bool
    __traceback__: TracebackType | None

    def __init__(
        self, name: str, message: str, code: StatusEnum, info: list[str] = [], *args: Any
    ) -> None: ...
    def __new__(
        cls,
        name: str,
        message: str,
        code: StatusEnum,
        info: list[str] = [],
        *args: Any,
        **kwds: Any,
    ) -> Self: ...
    def __setstate__(self, state: dict[str, Any] | None, /) -> None: ...

    if sys.version_info >= (3, 11):
        __notes__: list[str]

        def add_note(self, note: str, /) -> None: ...


class AbelDBException(BaseError):
    def __init__(self, message: str, code: StatusEnum, info=[], *args):
        super().__init__("AbelDBException", message, code, info, *args)
