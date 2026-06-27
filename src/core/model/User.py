from uuid import uuid4

from pydantic import BaseModel


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
