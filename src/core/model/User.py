from os import getenv, remove
from os.path import getsize, isdir, isfile
from pickle import (
    dump as pickle_dump,
)
from pickle import (
    load as pickle_load,
)
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from src.core.model.Connection import Connection
from src.core.model.Database import Database
from src.core.utils.constants import (
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
    RESTRICT_DB_PATH,
    RESTRICT_FILE,
    SETTINGS_NOT_FOUND,
)

load_dotenv()


class User(BaseModel):
    id: str = str(uuid4())
    username: str
    password: str


class UserCreate(User):
    port: str
    host: str


class UserConnect(UserCreate):
    database: str


class UserCreateDatabase(UserCreate):
    database: str


class UserDropDatabase(UserCreate):
    database: str


class UserOperation:
    @classmethod
    def __setup__(cls) -> bool:
        file = getenv(RESTRICT_FILE) or "restrict_null"
        print("setting database initial file")
        try:
            with open(file=file, mode="xb") as create:
                create.write(b"")
            print("file created")
        except FileExistsError:
            print("file already exists!")
        except Exception as e:
            print("unexpected error:", e)
            return False
        return True

    @classmethod
    async def user_create(cls, user: UserCreate) -> bool:
        cls.__setup__()

        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"
        data: list = []

        if getsize(file_path_name) > 0:
            with open(file=file_path_name, mode="rb") as file:
                raw = pickle_load(file)
                data = raw if isinstance(raw, list) else [raw]

        found_user = [
            u
            for u in data
            if (u["username"], u["host"], u["port"]) == (user.username, user.host, user.port)
        ]

        if found_user:
            raise Exception(
                f"user {user.username} already exists in port {user.port} and host {user.host}!"
            )

        data.append(user.model_dump())

        with open(file=file_path_name, mode="wb") as file:
            pickle_dump(data, file)

        with open(file=file_path_name, mode="rb") as file:
            saved: list = pickle_load(file)

        try:
            UserCreate.model_validate(saved[-1])
            print("user created")
            return True
        except ValidationError as e:
            print(e)
            return False

    @classmethod
    async def find_db_prefix_by_user_id(cls, user_id: str):
        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"

        with open(file=file_path_name, mode="rb") as file:
            raw = pickle_load(file)
            data = raw if isinstance(raw, list) else [raw]

        if not data:
            raise Exception(DATABASE_USER_NOT_FOUND)

        found_user = [user for user in data if user.id == user_id]

        if not found_user:
            raise Exception(DATABASE_USER_ID_NOT_FOUND)

        db_user: UserCreate = found_user[0]

        return f"{db_user.username}-{db_user.host}-{db_user.port}-"

    @classmethod
    async def database_connect(cls, user: UserConnect) -> Connection:
        print("connecting to database")

        if not user.database:
            raise Exception(DATABASE_NOT_SET)

        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"
        if not isfile(file_path_name):
            raise FileNotFoundError(file_path_name)
        if getsize(file_path_name) > 0:
            found = cls.__filter_db_user__(file_path_name=file_path_name, user=user)
            found_user = found[0]

            path = getenv(RESTRICT_DB_PATH) or "restrict_db_path"

            if not isdir(path):
                raise Exception(DATABASE_INVALID_PATH)

            file_name = cls.__db_name_formater__(
                username=found_user["username"],
                host=found_user["host"],
                port=found_user["port"],
                database=user.database,
            )

            file_db = path + file_name

            if not isfile(file_db):
                raise Exception(DATABASE_NOT_EXISTS)

            with open(file=file_db, mode="rb") as file:
                raw = pickle_load(file)
                data = raw if isinstance(raw, list) else [raw]

            if not data:
                raise Exception(DATABASE_EMPTY)

            found_db = data[0]

            if not found_db:
                raise Exception(FATAL_ERROR_DATABASE_NOT_FOUND)

            return Connection(Database.model_validate(found_db))
        else:
            raise Exception(SETTINGS_NOT_FOUND)

    @classmethod
    async def database_create(cls, user: UserCreateDatabase) -> None:
        print("creating a new database")

        if not user.database:
            raise Exception(DATABASE_NOT_SET)

        file_path_name = getenv(RESTRICT_FILE) or "restrict_null"
        if not isfile(file_path_name):
            raise FileNotFoundError(file_path_name)
        if getsize(file_path_name) > 0:
            found_user = cls.__filter_db_user__(file_path_name=file_path_name, user=user)

            db_user = found_user[0]

            database = Database(
                userId=db_user["id"],
                database=user.database,
            )

            path = getenv(RESTRICT_DB_PATH) or "restrict_db_path"

            if not isdir(path):
                raise Exception(DATABASE_INVALID_PATH)

            file_name = cls.__db_name_formater__(
                username=user.username,
                host=user.host,
                port=user.port,
                database=user.database,
            )
            file_db = path + file_name

            if isfile(file_db):
                raise Exception(DATABASE_ALREADY_EXISTS)

            with open(file=file_db, mode="wb") as file:
                pickle_dump(database, file)

            print("database created")
        else:
            raise Exception(SETTINGS_NOT_FOUND)

    @classmethod
    async def database_drop(cls, drop_user: UserDropDatabase) -> None:
        print("dropping database")

        path = getenv(RESTRICT_DB_PATH) or "restrict_db_path"

        if not isdir(path):
            raise Exception(DATABASE_INVALID_PATH)

        file_name = cls.__db_name_formater__(
            username=drop_user.username,
            host=drop_user.host,
            port=drop_user.port,
            database=drop_user.database,
        )
        file_db = path + file_name

        if not isfile(file_db):
            raise Exception(DATABASE_NOT_EXISTS)

        try:
            remove(file_db)
            print("database dropped")
        except OSError:
            raise Exception(DATABASE_UNEXPECT_DROP_ERROR)

    @classmethod
    def __filter_db_user__(
        cls, file_path_name: str, user: UserCreateDatabase | UserConnect | UserDropDatabase
    ) -> list:
        with open(file=file_path_name, mode="rb") as file:
            raw = pickle_load(file)
            data = raw if isinstance(raw, list) else [raw]

        found_user = [
            u
            for u in data
            if (u["username"], u["host"], u["port"]) == (user.username, user.host, user.port)
        ]

        if not found_user:
            raise Exception(ABELDB_USER_NOT_FOUND)

        return found_user

    @classmethod
    def __db_name_formater__(cls, username: str, host: str, port: str, database: str) -> str:
        return f"{username}-{host}-{port}-{database}.abel"
