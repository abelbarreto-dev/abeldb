from genericpath import getsize, isdir, isfile
from os import getenv, remove
from pickle import dump as pickle_dump
from pickle import load as pickle_load

from dotenv import load_dotenv
from pydantic import ValidationError

from src.core.model.Connection import Connection
from src.core.model.Database import Database
from src.core.model.User import UserConnect, UserCreate, UserCreateDatabase, UserDropDatabase
from src.exceptions.AbelDBException import AbelDBException
from src.utils.constants import (
    ABELDB_USER_NOT_FOUND,
    DATABASE_ALREADY_EXISTS,
    DATABASE_EMPTY,
    DATABASE_INVALID_PATH,
    DATABASE_NOT_EXISTS,
    DATABASE_NOT_SET,
    DATABASE_UNEXPECT_DROP_ERROR,
    DATABASE_USER_ID_NOT_FOUND,
    DATABASE_USER_NOT_FOUND,
    FATAL_ERROR_DATABASE_NOT_FOUND,
    READER_MODE,
    RESTRICT_DB_PATH,
    RESTRICT_FILE,
    SETTINGS_NOT_FOUND,
    SPECIAL_WRITER,
    WRITER_MODE,
)
from src.utils.status_enum import StatusEnum

load_dotenv()
READER: str = getenv(READER_MODE) or "reader_mode"
WRITER: str = getenv(WRITER_MODE) or "writer_mode"
SPECIAL_W: str = getenv(SPECIAL_WRITER) or "special_writer"


class UserOps:
    @classmethod
    async def user_create(cls, user: UserCreate) -> bool:
        cls.__setup__()

        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"
        data: list = []

        if getsize(file_path_name) > 0:
            with open(file=file_path_name, mode=READER) as file:
                raw = pickle_load(file)
                data = raw if isinstance(raw, list) else [raw]

        found_user = [
            u
            for u in data
            if (u["username"], u["host"], u["port"]) == (user.username, user.host, user.port)
        ]

        if found_user:
            raise AbelDBException(
                f"user {user.username} already exists in port {user.port} and host {user.host}",
                code=StatusEnum.CONFLICT,
                info=["database", "port", "host"],
            )

        data.append(user)

        with open(file=file_path_name, mode=WRITER) as file:
            pickle_dump(data, file)

        with open(file=file_path_name, mode=READER) as file:
            saved: list = pickle_load(file)

        try:
            UserCreate.model_validate(saved[-1])
            print("user created")
            return True
        except ValidationError as e:
            print(e)
            return False

    @classmethod
    def __setup__(cls) -> bool:
        file = getenv(RESTRICT_FILE) or "restrict_null"
        print("setting database initial file")
        try:
            with open(file=file, mode=SPECIAL_W) as create:
                create.write(b"")
            print("file created")
        except FileExistsError:
            print("file already exists!")
        except Exception as e:
            print("unexpected error:", e)
            return False
        return True

    @classmethod
    async def find_db_prefix_by_user_id(cls, user_id: str):
        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"

        with open(file=file_path_name, mode=READER) as file:
            raw = pickle_load(file)
            data = raw if isinstance(raw, list) else [raw]

        if not data:
            raise AbelDBException(
                DATABASE_USER_NOT_FOUND, code=StatusEnum.NOT_FOUND, info=["database", "not found"]
            )

        found_user = [user for user in data if user["id"] == user_id]

        if not found_user:
            raise AbelDBException(
                DATABASE_USER_ID_NOT_FOUND,
                code=StatusEnum.NOT_FOUND,
                info=["database", "user", "not found"],
            )

        db_user: UserCreate = UserCreate(**found_user[0])

        return f"{db_user.username}-{db_user.host}-{db_user.port}-"

    @classmethod
    async def database_connect(cls, user: UserConnect) -> Connection:
        print("connecting to database")

        if not user.database:
            raise AbelDBException(
                DATABASE_NOT_SET,
                code=StatusEnum.UNAUTHORIZED,
                info=["database", "settings not found", "unauthorized"],
            )

        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"
        if not isfile(file_path_name):
            raise FileNotFoundError(file_path_name)
        if getsize(file_path_name) > 0:
            found = cls.__filter_db_user__(file_path_name=file_path_name, user=user)
            found_user = found[0]

            path = getenv(RESTRICT_DB_PATH) or "restrict_db_path"

            if not isdir(path):
                raise AbelDBException(
                    DATABASE_INVALID_PATH,
                    code=StatusEnum.FORBIDDEN,
                    info=["database file", "not found", "path", "path"],
                )

            file_name = cls.__db_name_formater__(
                username=found_user["username"],
                host=found_user["host"],
                port=found_user["port"],
                database=user.database,
            )

            file_db = path + file_name

            if not isfile(file_db):
                raise AbelDBException(
                    DATABASE_NOT_EXISTS,
                    code=StatusEnum.NOT_FOUND,
                    info=["database", "not exists", file_name],
                )

            with open(file=file_db, mode=READER) as file:
                raw = pickle_load(file)
                data = raw if isinstance(raw, list) else [raw]

            if not data:
                raise AbelDBException(
                    DATABASE_EMPTY,
                    code=StatusEnum.FORBIDDEN,
                    info=["database data", "empty", "forbidden"],
                )

            found_db = data[0]

            if not found_db:
                raise AbelDBException(
                    FATAL_ERROR_DATABASE_NOT_FOUND,
                    code=StatusEnum.INTERNAL_ERROR,
                    info=["database", "fatal error", "not found", "connection"],
                )

            print("database connected")
            return Connection(Database.model_validate(found_db))
        else:
            raise AbelDBException(
                SETTINGS_NOT_FOUND,
                code=StatusEnum.UNAUTHORIZED,
                info=["settings database", "not found", "unauthorized"],
            )

    @classmethod
    async def database_create(cls, user: UserCreateDatabase) -> None:
        print("creating a new database")

        if not user.database:
            raise AbelDBException(
                DATABASE_NOT_SET,
                code=StatusEnum.UNAUTHORIZED,
                info=["database", "settings not found", "unauthorized"],
            )

        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"
        if not isfile(file_path_name):
            raise FileNotFoundError(file_path_name)
        if getsize(file_path_name) > 0:
            found_user = cls.__filter_db_user__(file_path_name=file_path_name, user=user)

            db_user = found_user[0]

            database = Database(
                userId=db_user["id"], database=user.database, table_files=[], relations=[]
            )

            path = getenv(RESTRICT_DB_PATH) or "restrict_db_path"

            if not isdir(path):
                raise AbelDBException(
                    DATABASE_INVALID_PATH,
                    code=StatusEnum.FORBIDDEN,
                    info=["database file", "not found", "path", "path"],
                )

            file_name = cls.__db_name_formater__(
                username=user.username,
                host=user.host,
                port=user.port,
                database=user.database,
            )
            file_db = path + file_name

            if isfile(file_db):
                raise AbelDBException(
                    DATABASE_ALREADY_EXISTS,
                    code=StatusEnum.CONFLICT,
                    info=["database", "conflict", "already exists", file_name],
                )

            with open(file=file_db, mode=WRITER) as file:
                pickle_dump(database, file)

            print("database created")
        else:
            raise AbelDBException(
                SETTINGS_NOT_FOUND,
                code=StatusEnum.UNAUTHORIZED,
                info=["settings database", "not found", "unauthorized"],
            )

    @classmethod
    def __filter_db_user__(
        cls, file_path_name: str, user: UserCreateDatabase | UserConnect | UserDropDatabase
    ) -> list:
        with open(file=file_path_name, mode=READER) as file:
            raw = pickle_load(file)
            data = raw if isinstance(raw, list) else [raw]

        found_user = [
            u
            for u in data
            if (u["username"], u["host"], u["port"]) == (user.username, user.host, user.port)
        ]

        if not found_user:
            raise AbelDBException(
                ABELDB_USER_NOT_FOUND,
                code=StatusEnum.NOT_FOUND,
                info=["databse", "user", "not found"],
            )

        return found_user

    @classmethod
    async def database_drop(cls, drop_user: UserDropDatabase) -> None:
        print("dropping database")

        path = getenv(RESTRICT_DB_PATH) or "restrict_db_path"

        if not isdir(path):
            raise AbelDBException(
                DATABASE_INVALID_PATH,
                code=StatusEnum.FORBIDDEN,
                info=["database file", "not found", "path", "path"],
            )

        file_name = cls.__db_name_formater__(
            username=drop_user.username,
            host=drop_user.host,
            port=drop_user.port,
            database=drop_user.database,
        )
        file_db = path + file_name

        if not isfile(file_db):
            raise AbelDBException(
                DATABASE_NOT_EXISTS,
                code=StatusEnum.NOT_FOUND,
                info=["database", "file not exists"],
            )

        try:
            remove(file_db)
            print("database dropped")
        except OSError:
            raise AbelDBException(
                DATABASE_UNEXPECT_DROP_ERROR,
                code=StatusEnum.INTERNAL_ERROR,
                info=["drop database", "unexpect error"],
            )

    @classmethod
    def __db_name_formater__(cls, username: str, host: str, port: str, database: str) -> str:
        return f"{username}-{host}-{port}-{database}.abel"
