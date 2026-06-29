import shutil
from genericpath import isdir, isfile
from os import getenv, remove
from pathlib import Path
from pickle import dump as pickle_dump
from pickle import load as pickle_load
from typing import Self

from dotenv import load_dotenv

from src.core.model.Connection import Connection
from src.core.model.Relation import Relation, RelationType
from src.core.model.Table import Column, Table, validate_column_params
from src.core.model.TableFile import TableFile
from src.core.operations.UserOps import UserOps
from src.exceptions.AbelDBException import AbelDBException
from src.utils.constants import (
    COLUMN_ALREADY_EXISTS,
    COLUMN_OVERRIDE_NOT_FOUND,
    DATABASE_NOT_FOUND,
    FOREIGN_KEY_ERROR,
    READER_MODE,
    RELATION_DROP_ERROR,
    RELATION_TABLE_NOT_FOUND,
    RELATION_UNDEFINED,
    RESTRICT_DB_PATH,
    RESTRICT_TABLES_PATH,
    TABLE_ALREADY_EXISTS,
    TABLE_COLUMNS_NOT_FOUND,
    TABLE_DROP_UNEXPECTED_ERROR,
    TABLE_NAME_INVALID,
    TABLE_NOT_EXISTS,
    TABLE_NOT_FOUND,
    UNEXPECTED_ALTER_TABLE_ERROR,
    WRITER_MODE,
)
from src.utils.status_enum import StatusEnum

load_dotenv()
READER: str = getenv(READER_MODE) or "reader_mode"
WRITER: str = getenv(WRITER_MODE) or "writer_mode"


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
        table_exists = sum((1 for pfl in self._db_.db.table_files if pfl.name == table.name)) == 1

        table.name = table.name.lower()

        if table_exists:
            raise AbelDBException(
                TABLE_ALREADY_EXISTS,
                code=StatusEnum.CONFLICT,
                info=[table.name, self._db_.db.database],
            )

        if len(table.table_body) == 0:
            raise AbelDBException(
                TABLE_COLUMNS_NOT_FOUND,
                code=StatusEnum.NOT_FOUND,
                info=["columns", self._db_.db.database],
            )

        for column in table.table_body:
            validate_column_params(column.model_dump())

        pk_count = sum((1 for row in table.table_body if row.params.is_primary_key))
        if pk_count != 1:
            raise AbelDBException(
                f"table must contains only one primary key -> {pk_count} found.",
                code=StatusEnum.BAD_REQUEST,
                info=["foreing key missing", "table", table.name],
            )

        table_file = self.__db_table_formater__(
            db_id=self._db_.db.id, database=self._db_.db.database, table=table.name
        )

        data_b = self._db_.db.model_copy()
        data_b.table_files.append(TableFile(name=table.name, file=table_file))

        db_prefix = await UserOps.find_db_prefix_by_user_id(user_id=data_b.userId)
        db_prefix += f"{data_b.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"

        table_path_file = f"{table_path}/{db_prefix}"

        if not isdir(table_path_file):
            folder = Path(table_path_file)
            folder.mkdir(parents=True, exist_ok=True)
            doc_dir = Path(table_path_file, "documents")
            doc_dir.mkdir(parents=True, exist_ok=True)

        table_path_file += f"/{table_file}"

        if isfile(table_path_file):
            raise AbelDBException(
                TABLE_ALREADY_EXISTS,
                code=StatusEnum.CONFLICT,
                info=["table conflit", "already exists", table.name],
            )

        database_file = getenv(RESTRICT_DB_PATH) or "database_path/"
        database_file += db_prefix

        if relact_table_name is not None:
            if relation_type is None:
                raise AbelDBException(
                    RELATION_UNDEFINED,
                    code=StatusEnum.BAD_REQUEST,
                    info=["relation between tables", "relation type undefined"],
                )

            found = tuple(
                table_db
                for table_db in data_b.table_files
                if relact_table_name.lower() == table_db.name.lower()
            )

            if found:
                file = found[0]
                data_b.relations.append(
                    Relation(
                        table_one_id=table.name.lower(),
                        table_two_id=file.name.lower(),
                        relation=relation_type,
                    )
                )
            else:
                raise AbelDBException(
                    RELATION_TABLE_NOT_FOUND,
                    code=StatusEnum.BAD_REQUEST,
                    info=["foreign key", "table reference", "not found"],
                )

            found = sum(
                (
                    1
                    for column in table.table_body
                    if column.params.is_foreign_key
                    and column.params.fK_foreign_table_name == relact_table_name
                )
            )

            if found == 0:
                raise AbelDBException(
                    FOREIGN_KEY_ERROR,
                    code=StatusEnum.FORBIDDEN,
                    info=[
                        "column",
                        "foreign key",
                        "table name referenced",
                        "at least one foreign key",
                    ],
                )
        else:
            for column in table.table_body:
                params = column.params
                if (
                    params.is_foreign_key
                    or params.fK_foreign_table_name
                    or params.fk_foreign_column_name
                ):
                    raise AbelDBException(
                        FOREIGN_KEY_ERROR,
                        code=StatusEnum.FORBIDDEN,
                        info=["databse", "table relation not found", "foreign key found"],
                    )

        if not isfile(database_file):
            raise AbelDBException(
                DATABASE_NOT_FOUND,
                code=StatusEnum.BAD_REQUEST,
                info=["dtatabase problem", "not found file", self._db_.db.database],
            )

        with open(file=table_path_file, mode=WRITER) as writer:
            pickle_dump(table, writer)
        with open(file=database_file, mode=WRITER) as writer:
            pickle_dump(data_b.model_dump(), writer)
        print(f"table '{table.name}' created!")

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
        filter_table = sum((1 for i in db.table_files if i.name.lower() == table_name.lower()))

        if filter_table == 0:
            raise AbelDBException(
                TABLE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["table not found", "tabe name in database", db.database],
            )

        db_prefix = await UserOps.find_db_prefix_by_user_id(user_id=db.userId)
        db_prefix += f"{db.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"
        table_path_file = f"{table_path}{db_prefix}"

        if not isdir(table_path_file):
            raise AbelDBException(
                TABLE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["table not found", table_name, db.database],
            )

        database_file = getenv(RESTRICT_DB_PATH) or "database_path/"

        database_file += db_prefix

        if not isfile(database_file):
            raise AbelDBException(
                DATABASE_NOT_FOUND,
                code=StatusEnum.NOT_FOUND,
                info=["database not found", db.database],
            )

        update_relations = ()

        for rel in db.relations:
            if table_name == rel.table_two_id:
                raise AbelDBException(
                    RELATION_DROP_ERROR,
                    code=StatusEnum.UNAUTHORIZED,
                    info=[
                        "table relation",
                        "breaks a drop",
                        f"table {table_name} relacts to {rel.table_one_id}",
                        f"relation type: {rel.relation.value}",
                    ],
                )

            if table_name == rel.table_one_id:
                with open(file=f"{table_path_file}/{rel.table_one_id}", mode=READER) as reader:
                    table: list = pickle_load(reader)
                with open(file=f"{table_path_file}/{rel.table_one_id}", mode=WRITER) as writer:
                    table.table_body = [
                        column for column in table.table_body if not column.params.is_foreign_key
                    ]
                    pickle_dump(table, writer)
                with open(file=f"{table_path_file}/{rel.table_two_id}", mode=READER) as reader:
                    table: list = pickle_load(reader)
                with open(file=f"{table_path_file}/{rel.table_two_id}", mode=WRITER) as writer:
                    table.table_body = [
                        column for column in table.table_body if not column.params.is_foreign_key
                    ]
                    pickle_dump(table, writer)
            update_relations += (rel,)

        db.relations = [rel for rel in update_relations]

        table_file = [
            file.file for file in db.table_files if file.name.lower() == table_name.lower()
        ][0]

        db.table_files = [table for table in db.table_files if table.name != table_name]

        with open(file=database_file, mode=WRITER) as writer:
            pickle_dump(db.model_dump(), writer)

        table_docs = f"{table_path_file}/documents"
        table_path_file += f"/{table_file}"

        try:
            remove(table_path_file)
            shutil.rmtree(table_docs, ignore_errors=True)
            doc_dir = Path(table_docs)
            doc_dir.mkdir(parents=True, exist_ok=True)
            print(f"table '{table_name}' dropped.")
        except OSError:
            raise AbelDBException(
                TABLE_DROP_UNEXPECTED_ERROR,
                code=StatusEnum.INTERNAL_ERROR,
                info=["table", "drop fail", table_name],
            )

    async def async_alter_table_column(
        self,
        table_name: str,
        column: Column,
        is_drop: bool = False,
        is_override: bool = False,
        column_override: str = None,
    ) -> None:
        """
        Async function to alter table adding a new column there. You send the name of the table,
        the column you want to add or drop, and your choice.

        If `is_drop` is true, the column will be deleted.

        If `is_override` is true, you must provide the column_override.

        * `column_override` represents the original column name you wanna change.
        """
        print(f"alter table process -> is_drop={is_drop} -> override={is_override}")

        if is_override and not column_override:
            raise AbelDBException(
                COLUMN_OVERRIDE_NOT_FOUND,
                code=StatusEnum.UNAUTHORIZED,
                info=["is_override", "column override", "name not found", "override true"],
            )

        db = self._db_.db

        table_exists = tuple(t for t in db.table_files if t.name == table_name)

        if len(table_exists) == 0:
            raise AbelDBException(
                TABLE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["table not exists", "not found", table_name],
            )

        table_file = table_exists[0].file

        db_prefix = await UserOps.find_db_prefix_by_user_id(user_id=db.userId)
        db_prefix += f"{db.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"
        table_path_file = f"{table_path}/{db_prefix}"

        if not isdir(table_path_file):
            raise AbelDBException(
                TABLE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["table not found", table_name, db.database],
            )

        table_path_file += f"/{table_file}"

        with open(file=table_path_file, mode=READER) as reader:
            tables = pickle_load(reader)
            target_table = tables

        if target_table.name != table_name:
            raise AbelDBException(
                TABLE_NOT_FOUND,
                code=StatusEnum.FORBIDDEN,
                info=["table", "does not match", "name"],
            )

        column_exists = sum((1 for tc in target_table.table_body if tc.name == column.name)) == 1

        if column_exists and not is_drop and not is_override:
            raise AbelDBException(
                COLUMN_ALREADY_EXISTS,
                code=StatusEnum.UNAUTHORIZED,
                info=["column", "name", "already exists", column.name],
            )

        if is_drop:
            target_table.table_body = [
                col for col in target_table.table_body if col.name != column.name
            ]
        elif not is_override:
            valid_column = validate_column_params(column.model_dump())
            column = Column(**valid_column)
            target_table.table_body.append(column)
        else:
            valid_column = validate_column_params(column.model_dump())
            column = Column(**valid_column)
            column_list = []
            for col in target_table.table_body:
                if column_override == col.name:
                    column_list.append(column)
                    continue
                column_list.append(col)
            target_table.table_body = column_list

        try:
            with open(file=table_path_file, mode=WRITER) as writer:
                pickle_dump(target_table, writer)
            print(f"table edited -> drop={is_drop} -> override={is_override}")
        except OSError:
            raise AbelDBException(
                UNEXPECTED_ALTER_TABLE_ERROR,
                code=StatusEnum.UNAUTHORIZED,
                info=["alter table", "add column", column.name],
            )

    async def async_alter_table_rename(self, table_name: str, new_table_name: str) -> None:
        """
        Async function to rename a table, you just send the current table name and the rename.
        Then, this function makes a query to check if the table exists and try to continue and
        rename the table and file.
        """
        print("alter table -> rename")

        table_name = table_name.lower()
        new_table_name = new_table_name.lower()

        if len(new_table_name) < 2:
            raise AbelDBException(
                TABLE_NAME_INVALID,
                code=StatusEnum.UNAUTHORIZED,
                info=[
                    "alter table",
                    "rename",
                    f"from: {table_name}",
                    f"to: {new_table_name}",
                    "smaller than 2 length",
                ],
            )

        db = self._db_.db

        table_exists = sum((1 for tf in db.table_files if tf.name == table_name)) == 1

        if not table_exists:
            raise AbelDBException(
                TABLE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["alter table rename", "not found", table_name],
            )

        original = self.__db_table_formater__(db_id=db.id, database=db.database, table=table_name)
        renamed = self.__db_table_formater__(
            db_id=db.id, database=db.database, table=new_table_name
        )

        db_prefix = await UserOps.find_db_prefix_by_user_id(user_id=db.userId)
        db_prefix += f"{db.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"
        table_path_file = f"{table_path}{db_prefix}"

        if not isdir(table_path_file):
            raise AbelDBException(
                TABLE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["table not found", table_name, db.database],
            )

        with open(file=f"{table_path_file}/{original}", mode=READER) as reader:
            tables = pickle_load(reader)
            target_table = tables

        if target_table.name != table_name:
            raise AbelDBException(
                TABLE_NOT_FOUND,
                code=StatusEnum.FORBIDDEN,
                info=["table", "does not match", "name"],
            )

        target_table.name = new_table_name

        with open(file=f"{table_path_file}/{renamed}", mode=WRITER) as writer:
            pickle_dump(target_table, writer)

        remove(f"{table_path_file}/{original}")

        db.table_files = [file for file in db.table_files if file.name != table_name]

        db.table_files.append(TableFile(name=target_table.name, file=renamed))

        database_file = getenv(RESTRICT_DB_PATH) or "database_path/"
        database_file += db_prefix

        if not isfile(database_file):
            raise AbelDBException(
                DATABASE_NOT_FOUND,
                code=StatusEnum.NOT_FOUND,
                info=["database not found", db.database],
            )

        with open(file=database_file, mode=WRITER) as writer:
            pickle_dump(db.model_dump(), writer)

        print(f"table '{table_name}' renamed to {new_table_name}!")

    def __db_table_formater__(self, db_id: str, database: str, table: str) -> str:
        return f"{db_id}-{database}-table-{table}.abel"

    async def async_find_table(self, table_name: str) -> Table:
        """
        Async function to find a table by its name. You send a name, the system search in database
        and if ok, the system search in files, if ok, it returns the table object.

        * If the table not found, it will raise an exception.
        """
        print(f"looking for a table named {table_name}...")

        db = self._db_.db

        file = [file.file for file in db.table_files if file.name == table_name]

        if len(file) == 0:
            raise AbelDBException(
                TABLE_NOT_FOUND,
                code=StatusEnum.NOT_FOUND,
                info=["table not found", table_name, "file"],
            )

        file = file[0]

        db_prefix = await UserOps.find_db_prefix_by_user_id(user_id=db.userId)
        db_prefix += f"{db.database}.abel"

        table_path = getenv(RESTRICT_TABLES_PATH) or "table_path"
        table_path_file = f"{table_path}{db_prefix}"

        with open(file=f"{table_path_file}/{file}", mode=READER) as reader:
            tables = pickle_load(reader)
            target_table = tables

        if target_table.name != table_name:
            raise AbelDBException(
                TABLE_NOT_FOUND,
                code=StatusEnum.FORBIDDEN,
                info=["table", "does not match", "name"],
            )

        print("table found!")
        return target_table

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._db_ = None
