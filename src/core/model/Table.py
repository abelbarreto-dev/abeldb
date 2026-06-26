from genericpath import isdir
from os import getenv, isfile
from pathlib import Path
from pickle import (
    dump as pickle_dump,
)
from typing import Any, Self
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from core.utils.column_util import validator_column_decorator
from core.utils.types_enum import TypesEnum
from src.core.model.Connection import Connection
from src.core.model.Relation import Relation, RelationType
from src.core.model.User import UserOperation

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


RESTRICT_TABLES_PATH: str = "RESTRICT_TABLES_PATH"
RESTRICT_DB_PATH: str = "RESTRICT_DB_PATH"


class TableOps:
    def __init__(self, db: Connection) -> None:
        self._db_ = db

    async def async_create_table(
        self, table: Table, relact_table_name: str = None, relation_type: RelationType = None
    ) -> None:
        print("creating table")
        if len(table.table_body) == 0:
            raise Exception("table must define at least one column")

        pk_count = sum(1 for row in table.table_body if row.primary_key)
        if pk_count != 1:
            raise Exception(f"table must contains only one primary key -> {pk_count} found.")

        table_file = self.__db_table_formater__(
            db_id=self._db_.db.id, database=self._db_.db.database, table=table.name
        )

        data_b = self._db_.db.model_copy()
        data_b.table_files.append(table_file)

        db_prefix = await UserOperation.find_db_prefix_by_user_id(user_id=data_b.userId)
        db_prefix += f"{data_b.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"

        table_path_file = f"{table_path}/{db_prefix}"

        if not isdir(table_path_file):
            folder = Path(table_path_file)
            folder.mkdir(parents=True, exist_ok=True)

        table_path_file += f"/{table_file}"

        if isfile(table_path_file):
            raise Exception("table aready exists.")

        database_file = getenv(RESTRICT_DB_PATH) or "database_path/"

        database_file += db_prefix

        if relact_table_name is not None:
            if relation_type is None:
                raise Exception("relation must be defined")

            found = (
                table_db
                for table_db in data_b.table_files
                if relact_table_name.lower() in table_db.lower()
            )

            if found:
                data_b.relations.append(
                    Relation(
                        table_one_id=table_file,
                        table_two_id=relact_table_name.lower(),
                        relation=relation_type,
                    )
                )

        with open(file=table_path_file, mode="wb") as writer:
            pickle_dump(table.model_dump(), writer)
        with open(file=database_file, mode="wb") as writer:
            pickle_dump(data_b.model_dump(), writer)
        print("table created!")

    async def async_drop_table(self, table_name: str) -> None:
        print("dropping table")
        db = self._db_.db
        filter_table = sum(1 for i in db.table_files if i.lower() == table_name.lower())

        if filter_table == 0:
            raise Exception("table not found")

        filter_table = sum(
            1 for rel in db.relations if table_name in (rel.table_one_id, rel.table_two_id)
        )

        # TODO: setar None nas relações e remover
        # TODO: remover relações onde temos None, None
        # TODO: remover coluna de chave estrangueira
        # TODO: dropar a tabela

        if filter_table > 0:
            raise Exception("current table has relationships.")

    async def async_alter_table(
        self, table_name: str, column: Column, is_drop: bool = False
    ) -> None:
        pass

    def __db_table_formater__(self, db_id: str, database: str, table: str) -> str:
        return f"{db_id}-{database}-table-{table}.abel"

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self) -> None:
        self._db_ = None
