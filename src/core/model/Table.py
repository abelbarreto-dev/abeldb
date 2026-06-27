from os import getenv, isdir, isfile, remove
from pathlib import Path
from pickle import (
    dump as pickle_dump,
)
from pickle import load as pickle_load
from typing import Any, Self
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from core.utils.column_util import validator_column_decorator
from core.utils.types_enum import TypesEnum
from src.core.model.Connection import Connection
from src.core.model.Relation import Relation, RelationType
from src.core.model.User import UserOperation
from src.core.utils.constants import (
    DATABASE_NOT_FOUND,
    FOREIGN_KEY_ERROR,
    RELATION_TABLE_NOT_FOUND,
    RELATION_UNDEFINED,
    RESTRICT_DB_PATH,
    RESTRICT_TABLES_PATH,
    TABLE_ALREADY_EXISTS,
    TABLE_COLUMNS_NOT_FOUND,
    TABLE_NOT_EXISTS,
)

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


class TableOps:
    def __init__(self, db: Connection) -> None:
        self._db_ = db

    async def async_create_table(
        self, table: Table, relact_table_name: str = None, relation_type: RelationType = None
    ) -> None:
        """
        Async function to create a new table of documents. You must send an object of Table, the
        table relacted to this table if possible, then you must send the relation type.

        Consider that you need a relation type in case of relation table be not None, else it will
        raise an exception. As well as you need at least a forengn key in case of relation table
        present.
        """
        print("creating table")
        table_exists = sum(1 for pfl in self._db_.db.table_files if pfl.name == table.name) == 0

        if table_exists:
            raise Exception(TABLE_ALREADY_EXISTS)

        if len(table.table_body) == 0:
            raise Exception(TABLE_COLUMNS_NOT_FOUND)

        pk_count = sum(1 for row in table.table_body if row.primary_key)
        if pk_count != 1:
            raise Exception(f"table must contains only one primary key -> {pk_count} found.")

        table_file = self.__db_table_formater__(
            db_id=self._db_.db.id, database=self._db_.db.database, table=table.name
        )

        data_b = self._db_.db.model_copy()
        data_b.table_files.append(**{"name": table.name, "file": table_file})

        db_prefix = await UserOperation.find_db_prefix_by_user_id(user_id=data_b.userId)
        db_prefix += f"{data_b.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"

        table_path_file = f"{table_path}/{db_prefix}"

        if not isdir(table_path_file):
            folder = Path(table_path_file)
            folder.mkdir(parents=True, exist_ok=True)

        table_path_file += f"/{table_file}"

        if isfile(table_path_file):
            raise Exception(TABLE_ALREADY_EXISTS)

        database_file = getenv(RESTRICT_DB_PATH) or "database_path/"

        database_file += db_prefix

        if relact_table_name is not None:
            if relation_type is None:
                raise Exception(RELATION_UNDEFINED)

            found = tuple(
                table_db
                for table_db in data_b.table_files
                if relact_table_name.lower() == table_db.name.lower()
            )

            if found:
                file = found[0]
                data_b.relations.append(
                    Relation(
                        table_one_id=table_file.lower(),
                        table_two_id=file.file.lower(),
                        relation=relation_type,
                    )
                )
            else:
                raise Exception(RELATION_TABLE_NOT_FOUND)

            found = sum(
                1
                for column in table.table_body
                if column.params.is_foreign_key
                and column.params.fK_foreign_table_name == relact_table_name
            )

            if found == 0:
                raise Exception(FOREIGN_KEY_ERROR)

        if not isfile(database_file):
            raise Exception(DATABASE_NOT_FOUND)

        with open(file=table_path_file, mode="wb") as writer:
            pickle_dump(table.model_dump(), writer)
        with open(file=database_file, mode="wb") as writer:
            pickle_dump(data_b.model_dump(), writer)
        print("table created!")

    async def async_drop_table(self, table_name: str) -> None:
        """
        Async function to drop a table. It has not return (None).
        You must send the table_name param, then:
        * It removes the relation;
        * It removes the column foreign key;
        * It removes the data;
        * It removes the table;
        """
        print("dropping table")
        db = self._db_.db
        filter_table = sum(1 for i in db.table_files if i.lower() == table_name.lower())

        if filter_table == 0:
            raise Exception(TABLE_NOT_EXISTS)

        db_prefix = await UserOperation.find_db_prefix_by_user_id(user_id=db.userId)
        db_prefix += f"{db.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"
        table_path_file = f"{table_path}/{db_prefix}"

        if not isdir(table_path_file):
            raise Exception(TABLE_NOT_EXISTS)

        database_file = getenv(RESTRICT_DB_PATH) or "database_path/"

        database_file += db_prefix

        if not isfile(database_file):
            raise Exception(DATABASE_NOT_FOUND)

        update_relations = ()

        for rel in db.relations:
            search = (rel.table_one_id, rel.table_two_id)
            if table_name in search:
                with open(file=f"{table_path_file}/{rel.table_one_id}", mode="rb") as reader:
                    table: list = pickle_load(reader)
                with open(file=f"{table_path_file}/{rel.table_one_id}", mode="wb") as writer:
                    table.table_body = [
                        column for column in table.table_body if not column.params.is_foreign_key
                    ]
                    pickle_dump(table, writer)
                with open(file=f"{table_path_file}/{rel.table_two_id}", mode="rb") as reader:
                    table: list = pickle_load(reader)
                with open(file=f"{table_path_file}/{rel.table_two_id}", mode="rb") as writer:
                    table.table_body = [
                        column for column in table.table_body if not column.params.is_foreign_key
                    ]
                    pickle_dump(table, writer)
            update_relations += (rel,)

        db.relations = [rel for rel in update_relations]

        db.table_files = [table for table in db.table_files if table != table_name]

        with open(file=database_file, mode="wb") as writer:
            pickle_dump(db.model_dump(), writer)

        table_path_file += f"/{table_name}"

        if isfile(table_path_file):
            remove(table_path_file)

        print("table dropped.")

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
