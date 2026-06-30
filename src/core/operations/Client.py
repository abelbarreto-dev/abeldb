from typing import Any, Self

from pydantic import BaseModel

from core.model.Connection import Connection
from core.model.Table import Table
from src.exceptions.AbelDBException import AbelDBException
from src.utils.constants import LOAD_TABLE_NAME_ERROR
from src.utils.status_enum import StatusEnum


class AbelDBClient:
    def __init__(self, connect: Connection) -> None:
        self.connect = connect
        self.table_name = None

    async def load(self, table: str) -> Self:
        files = self.connect.db.table_files

        found = sum((1 for file in files if file.name == table))

        self.table_name = table if found > 0 else None
        return self

    async def async_insert(self, table: BaseModel) -> BaseModel:
        await self.__check_table_name__()

    async def async_find_all(self, table: BaseModel) -> Table:
        await self.__check_table_name__()

    async def async_find_custom(self, **kwargs) -> Table:
        await self.__check_table_name__()

    async def async_update(self, doc_index: str, value: Any) -> Table:
        await self.__check_table_name__()

    async def async_delete(self, doc_index: str) -> Table:
        await self.__check_table_name__()

    async def async_soft_delete(self, doc_index: str) -> Table:
        await self.__check_table_name__()

    async def __check_table_name__(self) -> None:
        if not self.table_name:
            raise AbelDBException(
                LOAD_TABLE_NAME_ERROR,
                code=StatusEnum.UNAUTHORIZED,
                info=["table name", "load function problem", "database table", "none found"],
            )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.connect = None
        self.table = None
