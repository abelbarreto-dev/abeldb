import asyncio
from typing import Any, Self

from pydantic import BaseModel

from core.model.Connection import Connection
from core.model.Table import Table


class AbelDBClient:
    def __init__(self, connect: Connection, table: type[BaseModel]) -> None:
        self.connect = connect
        self.table = table

    # ── sync ────────────────────────────────────────────────────────────────

    def insert(self, **kwargs) -> BaseModel:
        data = self.table.model_validate(kwargs)
        return data

    def find_by_doc_index(self, doc_index: str) -> Table:
        pass

    def find_all(self) -> Table:
        pass

    def find_custom(self, **kwargs) -> Table:
        pass

    def update(self, doc_index: str, value: Any) -> Table:
        pass

    def delete(self, doc_index: str) -> Table:
        pass

    def soft_delete(self, doc_index: str) -> Table:
        pass

    # ── async ────────────────────────────────────────────────────────────────

    async def async_insert(self, **kwargs) -> BaseModel:
        return await asyncio.to_thread(self.insert, **kwargs)

    async def async_find_by_doc_index(self, doc_index: str) -> Table:
        return await asyncio.to_thread(self.find_by_doc_index, doc_index)

    async def async_find_all(self) -> Table:
        return await asyncio.to_thread(self.find_all)

    async def async_find_custom(self, **kwargs) -> Table:
        return await asyncio.to_thread(self.find_custom, **kwargs)

    async def async_update(self, doc_index: str, value: Any) -> Table:
        return await asyncio.to_thread(self.update, doc_index, value)

    async def async_delete(self, doc_index: str) -> Table:
        return await asyncio.to_thread(self.delete, doc_index)

    async def async_soft_delete(self, doc_index: str) -> Table:
        return await asyncio.to_thread(self.soft_delete, doc_index)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.connect = None
        self.table = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.connect = None
        self.table = None
